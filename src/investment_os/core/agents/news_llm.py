from __future__ import annotations

from investment_os.core.agents.base import Analyst
from investment_os.core.agents.grounded import parse_grounded_opinion
from investment_os.core.llm import LLMClient, LLMError, LLMRequest
from investment_os.domain import AnalystOpinion, MarketBrief
from investment_os.knowledge.ports import CuratedNews, MarketSnapshot
from investment_os.llm.promptstore import PromptStore
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_SYSTEM = (
    "Anda analis berita pasar modal Indonesia. Balas hanya dengan JSON valid "
    "sesuai skema yang diminta, tanpa teks apa pun di luar objek JSON."
)


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
        return parse_grounded_opinion(self.role, text, allowed)
