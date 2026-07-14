"""Investment Committee orchestration.

Wires the graph from docs/fase-2-ai-architecture/02-langgraph-workflow.md:

    load_context -> route_analysts -> run_analysts
        -> [insufficient evidence] -> abstain -> END
        -> build_cases -> committee_review -> decide -> END

Confidence and rules interlock in two passes inside ``decide``: verdict-shaping
rules run first, the number of conflicts they raise feeds the confidence
score, and the confidence floor (R3) is checked against that final number.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from investment_os.core.agents import committee
from investment_os.core.agents.base import Analyst
from investment_os.core.confidence import ConfidenceBreakdown, ConfidenceEngine
from investment_os.core.decision import DecisionEngine
from investment_os.core.decision.rules import DecisionFacts
from investment_os.core.explain import AnalysisReport, build_report
from investment_os.core.explain.narrator import Narrator
from investment_os.core.graph import END, AnalysisState, Graph, NodeError
from investment_os.core.market_intel import MarketBriefBuilder
from investment_os.core.ports import RecommendationStore
from investment_os.domain import (
    AnalystOpinion,
    Argument,
    Decision,
    FlowRegime,
    MarketBrief,
    RuleTrigger,
    Side,
    Verdict,
)
from investment_os.knowledge.ports import KnowledgeBase
from investment_os.observability import bind_run_context, get_logger, metrics

log = get_logger(__name__)

# Stamped onto every stored recommendation; becomes the model/prompt version
# pair once LLM analysts land (docs/fase-3, recommendations schema).
ENGINE_VERSION = "heuristic-0.1.0"


class TickerNotFoundError(LookupError):
    def __init__(self, ticker: str) -> None:
        super().__init__(f"ticker '{ticker}' tidak ada di knowledge base")
        self.ticker = ticker


class AnalysisResult(BaseModel):
    report: AnalysisReport
    brief: MarketBrief


class AnalysisService:
    def __init__(
        self,
        kb: KnowledgeBase,
        analysts: list[Analyst],
        *,
        decision_engine: DecisionEngine | None = None,
        confidence_engine: ConfidenceEngine | None = None,
        min_evidence: int = 3,
        stale_after_days: float = 7.0,
        low_confidence_threshold: float = 0.6,
        analyst_timeout_s: float = 30.0,
        recommendation_store: RecommendationStore | None = None,
        narrator: Narrator | None = None,
    ) -> None:
        self._kb = kb
        self._analysts = analysts
        self._decision_engine = decision_engine or DecisionEngine()
        self._confidence_engine = confidence_engine or ConfidenceEngine()
        self._brief_builder = MarketBriefBuilder(kb)
        self._min_evidence = min_evidence
        self._stale_after_days = stale_after_days
        self._low_confidence_threshold = low_confidence_threshold
        self._analyst_timeout_s = analyst_timeout_s
        self._store = recommendation_store
        self._narrator = narrator
        self._graph = self._build_graph()

    async def analyze(self, ticker: str) -> AnalysisResult:
        symbol = ticker.strip().upper()
        with bind_run_context(ticker=symbol) as run_id:
            log.info("analysis_started")
            state = AnalysisState(ticker=symbol, as_of=dt.datetime.now(tz=dt.UTC))
            try:
                final = await self._graph.run(state)
            except NodeError as exc:
                # Domain errors keep their type across the graph boundary.
                if isinstance(exc.cause, TickerNotFoundError):
                    raise exc.cause from None
                raise
            assert final.market_brief is not None
            report = build_report(final)
            report = await self._narrate(report, final.market_brief)
            await self._persist(report, run_id=run_id, as_of=final.as_of)
            metrics.increment("analysis_completed", verdict=report.decision.verdict.value)
            log.info(
                "analysis_completed",
                verdict=report.decision.verdict.value,
                confidence=report.decision.confidence,
            )
            return AnalysisResult(report=report, brief=final.market_brief)

    def daily_brief(self, date: dt.date | None = None) -> MarketBrief:
        return self._brief_builder.build(date or dt.datetime.now(tz=dt.UTC).date())

    async def _narrate(self, report: AnalysisReport, brief: MarketBrief) -> AnalysisReport:
        if self._narrator is None:
            return report
        result = await self._narrator.narrate(report, brief)
        if result is None:
            return report
        return report.model_copy(
            update={
                "narrative": result.text,
                "llm_version": result.llm_version,
                "prompt_version": result.prompt_version,
            }
        )

    async def _persist(self, report: AnalysisReport, *, run_id: str, as_of: dt.datetime) -> None:
        """Best-effort: a storage failure must never cost the user their answer."""
        if self._store is None:
            return
        try:
            rec_id = await asyncio.to_thread(
                self._store.save,
                report,
                run_id=run_id,
                engine_version=ENGINE_VERSION,
                as_of=as_of,
            )
            log.info("recommendation_stored", rec_id=rec_id)
        except Exception:
            metrics.increment("recommendation_store_failures")
            log.exception("recommendation_store_failed")

    # -- graph nodes ---------------------------------------------------------

    def _build_graph(self) -> Graph[AnalysisState]:
        graph: Graph[AnalysisState] = Graph(name="investment-committee")
        graph.add_node("load_context", self._load_context)
        graph.add_node("route_analysts", self._route_analysts)
        graph.add_node("run_analysts", self._run_analysts)
        graph.add_node("abstain", self._abstain)
        graph.add_node("build_cases", self._build_cases)
        graph.add_node("committee_review", self._committee_review)
        graph.add_node("decide", self._decide)

        graph.add_edge("load_context", "route_analysts")
        graph.add_edge("route_analysts", "run_analysts")
        graph.add_edge(
            "run_analysts", "abstain", condition=lambda s: s.evidence_count < self._min_evidence
        )
        graph.add_edge("run_analysts", "build_cases")
        graph.add_edge("build_cases", "committee_review")
        graph.add_edge("committee_review", "decide")
        graph.add_edge("abstain", END)
        graph.add_edge("decide", END)
        return graph

    async def _load_context(self, state: AnalysisState) -> Mapping[str, Any]:
        snapshot = self._kb.snapshot(state.ticker)
        if snapshot is None:
            raise TickerNotFoundError(state.ticker)
        brief = self._brief_builder.build(snapshot.as_of.date())
        return {
            "snapshot": snapshot,
            "market_brief": brief,
            # Anchor the run to the knowledge base's data time, not wall clock:
            # freshness and staleness must be judged against what the system
            # actually knows, and runs must be reproducible for audit.
            "as_of": snapshot.as_of,
            "_audit_note": f"context loaded, market {brief.sentiment.value.lower()}",
        }

    async def _route_analysts(self, state: AnalysisState) -> Mapping[str, Any]:
        assert state.snapshot is not None
        selected = [a.role for a in self._analysts if a.is_relevant(state.snapshot)]
        skipped = [a.role for a in self._analysts if a.role not in selected]
        note = f"selected: {', '.join(selected) or 'none'}"
        if skipped:
            note += f" · skipped: {', '.join(skipped)}"
        return {"selected_roles": selected, "_audit_note": note}

    async def _run_analysts(self, state: AnalysisState) -> Mapping[str, Any]:
        assert state.snapshot is not None and state.market_brief is not None
        active = [a for a in self._analysts if a.role in state.selected_roles]

        async def guarded(analyst: Analyst) -> AnalystOpinion | Exception:
            try:
                assert state.snapshot is not None and state.market_brief is not None
                return await asyncio.wait_for(
                    analyst.assess(state.snapshot, state.market_brief),
                    timeout=self._analyst_timeout_s,
                )
            except Exception as exc:
                return exc

        results = await asyncio.gather(*(guarded(a) for a in active))

        outputs: dict[str, AnalystOpinion] = {}
        degraded: list[str] = []
        for analyst, result in zip(active, results, strict=True):
            if isinstance(result, Exception):
                degraded.append(analyst.role)
                log.warning("analyst_failed", role=analyst.role, error=repr(result))
            else:
                outputs[analyst.role] = result

        return {
            "analyst_outputs": outputs,
            "degraded_roles": degraded,
            "_audit_note": f"{len(outputs)} opini, {len(degraded)} gagal",
        }

    async def _abstain(self, state: AnalysisState) -> Mapping[str, Any]:
        breakdown = self._confidence_engine.score(
            state.analyst_outputs, now=state.as_of, rule_conflicts=1
        )
        decision = Decision(
            verdict=Verdict.ABSTAIN,
            proposed_verdict=Verdict.ABSTAIN,
            confidence=breakdown.calibrated,
            confidence_band=breakdown.band,
            reasons=["Bukti tidak memadai untuk mengambil posisi."],
            triggered_rules=[
                RuleTrigger(
                    rule_id="R2",
                    reason="Bukti tidak memadai untuk mengambil posisi.",
                    effect="FORCE ABSTAIN",
                )
            ],
            requires_review=True,
        )
        return {
            "decision": decision,
            "confidence_factors": _factors(breakdown),
            "bull_case": Argument(side=Side.BULL, points=[]),
            "bear_case": Argument(side=Side.BEAR, points=[]),
            "committee_notes": [
                f"Evidence terkumpul {state.evidence_count} < minimum {self._min_evidence}."
            ],
            "_audit_note": "insufficient evidence — abstained",
        }

    async def _build_cases(self, state: AnalysisState) -> Mapping[str, Any]:
        opinions = list(state.analyst_outputs.values())
        bull = committee.build_case(opinions, Side.BULL)
        bear = committee.build_case(opinions, Side.BEAR)
        return {
            "bull_case": bull,
            "bear_case": bear,
            "_audit_note": f"bull {bull.strength:.2f} vs bear {bear.strength:.2f}",
        }

    async def _committee_review(self, state: AnalysisState) -> Mapping[str, Any]:
        role_weights = {a.role: a.weight for a in self._analysts}
        score = committee.consensus_score(state.analyst_outputs, role_weights)
        notes = committee.consistency_notes(state.analyst_outputs)
        if state.degraded_roles:
            notes.append(f"Analis gagal dan dilewati: {', '.join(state.degraded_roles)}")
        return {
            "proposed_score": round(score, 4),
            "committee_notes": notes,
            "_audit_note": f"consensus {score:+.3f}",
        }

    async def _decide(self, state: AnalysisState) -> Mapping[str, Any]:
        proposed = committee.propose_verdict(state.proposed_score)

        facts = self._facts(state, confidence=1.0)
        first_pass = self._decision_engine.evaluate(proposed, facts)
        conflicts = sum(1 for t in first_pass.triggers if t.effect.startswith(("FORCE", "CAP")))

        breakdown = self._confidence_engine.score(
            state.analyst_outputs, now=state.as_of, rule_conflicts=conflicts
        )

        outcome = self._decision_engine.evaluate(
            proposed, self._facts(state, confidence=breakdown.calibrated)
        )

        reasons = [
            f"Skor konsensus komite {state.proposed_score:+.2f} "
            f"({len(state.analyst_outputs)} analis)."
        ]
        reasons.extend(t.reason for t in outcome.triggers if t.effect != "FLAG_REVIEW")

        decision = Decision(
            verdict=outcome.verdict,
            proposed_verdict=proposed,
            confidence=breakdown.calibrated,
            confidence_band=breakdown.band,
            reasons=reasons,
            triggered_rules=outcome.triggers,
            requires_review=outcome.requires_review,
        )
        return {
            "decision": decision,
            "confidence_factors": _factors(breakdown),
            "_audit_note": f"{proposed.value} -> {outcome.verdict.value} "
            f"(conf {breakdown.calibrated:.2f} {breakdown.band})",
        }

    def _facts(self, state: AnalysisState, *, confidence: float) -> DecisionFacts:
        fundamental = state.analyst_outputs.get("fundamental")
        news = state.analyst_outputs.get("news")
        flow = state.analyst_outputs.get("foreign_flow")

        flow_regime: FlowRegime | None = None
        if flow is not None and "flow_regime" in flow.signals:
            flow_regime = FlowRegime(flow.signals["flow_regime"])

        evidence_ages = [
            ref.age_days(state.as_of)
            for opinion in state.analyst_outputs.values()
            for ref in opinion.evidence
        ]
        data_stale = not evidence_ages or min(evidence_ages) > self._stale_after_days

        return DecisionFacts(
            fundamental_stance=fundamental.stance if fundamental else None,
            fundamental_score=fundamental.score if fundamental else 0.0,
            news_stance=news.stance if news else None,
            flow_regime=flow_regime,
            evidence_count=state.evidence_count,
            min_evidence=self._min_evidence,
            data_stale=data_stale,
            confidence=confidence,
            low_confidence_threshold=self._low_confidence_threshold,
        )


def _factors(breakdown: ConfidenceBreakdown) -> dict[str, float]:
    return {
        "evidence_strength": breakdown.evidence_strength,
        "freshness": breakdown.freshness,
        "agreement": breakdown.agreement,
        "source_quality": breakdown.source_quality,
    }
