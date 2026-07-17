from __future__ import annotations

import json
import re

from investment_os.core.agents.base import Analyst
from investment_os.core.llm import LLMClient, LLMError, LLMRequest
from investment_os.domain import AnalystOpinion, MarketBrief, Stance
from investment_os.knowledge.ports import CuratedNews, MarketSnapshot
from investment_os.llm.promptstore import PromptStore
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_SYSTEM = (
    "Anda analis berita pasar modal Indonesia. Balas hanya dengan JSON valid "
    "sesuai skema yang diminta, tanpa teks apa pun di luar objek JSON."
)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_MAX_CONFIDENCE = 0.9


class LlmNewsAnalyst:
    """News reasoning via LLM, constrained to curated KnowledgeBase records.

    The wrapped deterministic analyst stays in charge of relevance and takes
    over on any failure — provider error, malformed JSON, out-of-range values,
    or a citation that does not exist in the snapshot. The committee therefore
    never loses its news voice, and every accepted opinion is fully grounded.
    """

    role = "news"

    def __init__(
        self,
        llm: LLMClient,
        prompts: PromptStore,
        fallback: Analyst,
        *,
        max_items: int = 10,
        max_tokens: int = 600,
        prompt_version: int | None = None,
    ) -> None:
        self.weight = fallback.weight
        self._llm = llm
        self._template = prompts.get("news_analyst", prompt_version)
        self._fallback = fallback
        self._max_items = max_items
        self._max_tokens = max_tokens

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return self._fallback.is_relevant(snapshot)

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        items = snapshot.news[: self._max_items]
        try:
            response = await self._llm.complete(
                LLMRequest(
                    system=_SYSTEM,
                    prompt=self._render(snapshot, brief, items),
                    max_tokens=self._max_tokens,
                )
            )
            opinion = self._parse(response.text, {item.ref_id: item for item in items})
        except (LLMError, ValueError) as exc:
            metrics.increment("llm_analyst_fallbacks", role=self.role)
            log.warning(
                "llm_analyst_fallback",
                role=self.role,
                ticker=snapshot.profile.ticker,
                error=str(exc),
            )
            return await self._fallback.assess(snapshot, brief)

        metrics.increment("llm_analyst_assessments", role=self.role)
        return opinion.model_copy(
            update={"signals": {**opinion.signals, "llm_version": response.version_tag}}
        )

    def _render(
        self, snapshot: MarketSnapshot, brief: MarketBrief, items: list[CuratedNews]
    ) -> str:
        news_lines = "\n".join(
            f"- [{item.ref_id}] ({item.published_at:%Y-%m-%d}, {item.source}, "
            f"reliabilitas {item.reliability:.2f}) {item.title} — {item.summary}"
            for item in items
        )
        return self._template.render(
            ticker=snapshot.profile.ticker,
            company=snapshot.profile.name,
            sector=snapshot.profile.sector,
            as_of=f"{snapshot.as_of:%Y-%m-%d}",
            market_context=(
                f"sentimen {brief.sentiment.value.lower()}, IHSG {brief.index_change_pct:+.2f}%"
            ),
            news=news_lines,
        )

    def _parse(self, text: str, allowed: dict[str, CuratedNews]) -> AnalystOpinion:
        match = _JSON_RE.search(text)
        if match is None:
            raise ValueError("respons tidak memuat JSON")
        payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("JSON bukan objek")

        score = _number(payload, "score", low=-1.0, high=1.0)
        confidence = min(_number(payload, "confidence", low=0.0, high=1.0), _MAX_CONFIDENCE)

        key_points = _strings(payload.get("key_points"))[:5]
        if not key_points:
            raise ValueError("key_points kosong")

        cited = _strings(payload.get("evidence_refs"))
        if not cited:
            raise ValueError("tanpa sitasi evidence_refs")
        unknown = [ref for ref in cited if ref not in allowed]
        if unknown:
            raise ValueError(f"sitasi tidak dikenal: {unknown}")

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=[allowed[ref].as_evidence() for ref in dict.fromkeys(cited)][:5],
            confidence=confidence,
            caveats=_strings(payload.get("caveats"))[:3],
            signals={"engine": "llm"},
        )


def _number(payload: dict[str, object], key: str, *, low: float, high: float) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} bukan angka")
    if not low <= float(value) <= high:
        raise ValueError(f"{key} di luar rentang [{low}, {high}]: {value}")
    return float(value)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
