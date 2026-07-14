"""Explainability: assemble a fully-attributed report from graph state.

The report is interface-agnostic structured data; rendering (Telegram HTML,
web, API JSON) happens in the interface adapters. Everything here must be
reconstructable — verdict, the rules that shaped it, the evidence behind each
argument, and the per-node audit trail.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from investment_os.core.graph.state import AnalysisState
from investment_os.domain import Argument, AuditEvent, Decision, EvidenceRef


class AnalysisReport(BaseModel):
    ticker: str
    company: str
    sector: str
    decision: Decision
    headline: str
    bull_case: Argument
    bear_case: Argument
    committee_notes: list[str]
    risks: list[str]
    evidence: list[EvidenceRef]
    confidence_factors: dict[str, float]
    degraded_roles: list[str] = Field(default_factory=list)
    audit_trail: list[AuditEvent] = Field(default_factory=list)


def build_report(state: AnalysisState) -> AnalysisReport:
    if state.decision is None or state.snapshot is None:
        raise ValueError("state is missing decision or snapshot")
    if state.bull_case is None or state.bear_case is None:
        raise ValueError("state is missing bull/bear cases")

    risks: list[str] = []
    seen_risks: set[str] = set()
    for opinion in state.analyst_outputs.values():
        for caveat in opinion.caveats:
            if caveat not in seen_risks:
                seen_risks.add(caveat)
                risks.append(caveat)

    evidence: list[EvidenceRef] = []
    seen_refs: set[str] = set()
    for opinion in state.analyst_outputs.values():
        for ref in opinion.evidence:
            key = f"{ref.source}:{ref.ref_id}"
            if key not in seen_refs:
                seen_refs.add(key)
                evidence.append(ref)

    return AnalysisReport(
        ticker=state.ticker,
        company=state.snapshot.profile.name,
        sector=state.snapshot.profile.sector,
        decision=state.decision,
        headline=_headline(state),
        bull_case=state.bull_case,
        bear_case=state.bear_case,
        committee_notes=state.committee_notes,
        risks=risks,
        evidence=evidence,
        confidence_factors=dict(state.confidence_factors),
        degraded_roles=state.degraded_roles,
        audit_trail=state.audit_trail,
    )


def _headline(state: AnalysisState) -> str:
    decision = state.decision
    assert decision is not None
    if decision.triggered_rules and decision.verdict != decision.proposed_verdict:
        return decision.triggered_rules[0].reason
    if decision.reasons:
        return decision.reasons[0]
    return f"Komite mengusulkan {decision.verdict.value} dengan skor {state.proposed_score:+.2f}."
