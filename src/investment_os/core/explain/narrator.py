from __future__ import annotations

from dataclasses import dataclass

from investment_os.core.explain.guard import narrative_violations
from investment_os.core.explain.report import AnalysisReport
from investment_os.core.llm import LLMClient, LLMError, LLMRequest
from investment_os.domain import MarketBrief
from investment_os.llm.promptstore import PromptStore
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_SYSTEM = (
    "Anda menulis narasi riset investasi berbahasa Indonesia yang ringkas, "
    "faktual, dan tunduk pada aturan di prompt."
)


@dataclass(frozen=True)
class NarrativeResult:
    text: str
    llm_version: str
    prompt_version: str


class Narrator:
    def __init__(
        self,
        llm: LLMClient,
        prompts: PromptStore,
        *,
        prompt_version: int | None = None,
        max_tokens: int = 700,
    ) -> None:
        self._llm = llm
        self._template = prompts.get("cio_narrative", prompt_version)
        self._max_tokens = max_tokens

    async def narrate(self, report: AnalysisReport, brief: MarketBrief) -> NarrativeResult | None:
        prompt = self._render_prompt(report, brief)
        try:
            response = await self._llm.complete(
                LLMRequest(system=_SYSTEM, prompt=prompt, max_tokens=self._max_tokens)
            )
        except LLMError as exc:
            metrics.increment("narrative_failures", reason="llm_error")
            log.warning("narrative_llm_failed", error=str(exc))
            return None

        if not response.text:
            metrics.increment("narrative_failures", reason="empty")
            return None

        violations = narrative_violations(response.text, self._allowed_sources(report, prompt))
        if violations:
            metrics.increment("narrative_failures", reason="guard_rejected")
            log.warning("narrative_guard_rejected", violations=violations)
            return None

        return NarrativeResult(
            text=response.text,
            llm_version=response.version_tag,
            prompt_version=self._template.tag,
        )

    def _render_prompt(self, report: AnalysisReport, brief: MarketBrief) -> str:
        decision = report.decision
        findings = [
            f"- {point.claim}"
            for case in (report.bull_case, report.bear_case)
            for point in case.points
        ]
        rules = [
            f"- [{t.rule_id}] {t.reason}"
            for t in decision.triggered_rules
            if t.effect != "FLAG_REVIEW"
        ]
        return self._template.render(
            market_context=(
                f"sentimen {brief.sentiment.value.lower()}, IHSG {brief.index_change_pct:+.2f}%"
            ),
            ticker=report.ticker,
            company=report.company,
            sector=report.sector,
            verdict=decision.verdict.value,
            confidence_pct=f"{decision.confidence * 100:.0f}",
            band=decision.confidence_band,
            consensus=", ".join(decision.reasons[:1]) or "-",
            findings="\n".join(findings) or "- (tidak ada)",
            rules="\n".join(rules) or "- (tidak ada)",
            risks="\n".join(f"- {r}" for r in report.risks) or "- (tidak ada)",
        )

    def _allowed_sources(self, report: AnalysisReport, prompt: str) -> list[str]:
        # Everything shown to the model is fair game to repeat — nothing else.
        return [prompt, *(ref.summary for ref in report.evidence)]
