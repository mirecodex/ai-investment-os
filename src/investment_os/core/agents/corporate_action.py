from __future__ import annotations

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.grounded import parse_grounded_opinion
from investment_os.core.llm import LLMClient, LLMError, LLMRequest
from investment_os.domain import AnalystOpinion, MarketBrief
from investment_os.knowledge.ports import CuratedNews, MarketSnapshot
from investment_os.llm.promptstore import PromptStore
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_SYSTEM = (
    "Anda analis aksi korporasi pasar modal Indonesia. Balas hanya dengan "
    "JSON valid sesuai skema yang diminta, tanpa teks di luar objek JSON."
)
_ACTION_TERMS = (
    "dividen",
    "rights issue",
    "right issue",
    "buyback",
    "beli kembali saham",
    "akuisisi",
    "merger",
    "stock split",
    "pemecahan saham",
    "private placement",
    "tender offer",
    "divestasi",
    "spin-off",
)


class CorporateActionAnalyst:
    """Extra committee seat that only exists when LLM analysts are enabled.

    Deterministic keyword gate decides relevance; the LLM only judges impact
    (dilution, cash return, control change) of disclosure-style news. There is
    no heuristic that can do this judgement, so on any failure the seat
    recuses (AnalystError) exactly like data-starved analysts in live mode —
    the committee proceeds and the decision never depends on the LLM.
    """

    role = "corporate_action"
    weight = 0.8

    def __init__(
        self,
        llm: LLMClient,
        prompts: PromptStore,
        *,
        max_items: int = 8,
        max_tokens: int = 600,
        prompt_version: int | None = None,
    ) -> None:
        self._llm = llm
        self._template = prompts.get("corporate_action_analyst", prompt_version)
        self._max_items = max_items
        self._max_tokens = max_tokens

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return bool(self._action_items(snapshot))

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        items = self._action_items(snapshot)
        if not items:
            raise AnalystError(f"{snapshot.profile.ticker}: tidak ada berita aksi korporasi")
        try:
            response = await self._llm.complete(
                LLMRequest(
                    system=_SYSTEM,
                    prompt=self._render(snapshot, items),
                    max_tokens=self._max_tokens,
                )
            )
            opinion = parse_grounded_opinion(
                self.role, response.text, {item.ref_id: item for item in items}
            )
        except (LLMError, ValueError) as exc:
            metrics.increment("llm_analyst_recusals", role=self.role)
            log.warning(
                "llm_analyst_recused",
                role=self.role,
                ticker=snapshot.profile.ticker,
                error=str(exc),
            )
            raise AnalystError(f"corporate_action recuse: {exc}") from exc

        metrics.increment("llm_analyst_assessments", role=self.role)
        return opinion.model_copy(
            update={"signals": {**opinion.signals, "llm_version": response.version_tag}}
        )

    def _action_items(self, snapshot: MarketSnapshot) -> list[CuratedNews]:
        matched = [
            item
            for item in snapshot.news
            if any(term in f"{item.title} {item.summary}".lower() for term in _ACTION_TERMS)
        ]
        return matched[: self._max_items]

    def _render(self, snapshot: MarketSnapshot, items: list[CuratedNews]) -> str:
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
            news=news_lines,
        )
