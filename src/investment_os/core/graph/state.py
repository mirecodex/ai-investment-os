"""Shared state for the Investment Committee graph.

Mirrors ``AnalysisState`` in docs/fase-2-ai-architecture/02-langgraph-workflow.md.
State is immutable per node: each node returns a patch, the runtime applies it
as a copy, so a failed node can never leave half-written state behind.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from investment_os.domain import AnalystOpinion, Argument, AuditEvent, Decision, MarketBrief
from investment_os.knowledge.ports import MarketSnapshot


class AnalysisState(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    as_of: dt.datetime
    market_brief: MarketBrief | None = None
    snapshot: MarketSnapshot | None = None
    selected_roles: list[str] = Field(default_factory=list)
    analyst_outputs: dict[str, AnalystOpinion] = Field(default_factory=dict)
    bull_case: Argument | None = None
    bear_case: Argument | None = None
    committee_notes: list[str] = Field(default_factory=list)
    proposed_score: float = 0.0
    decision: Decision | None = None
    confidence_factors: dict[str, float] = Field(default_factory=dict)
    audit_trail: list[AuditEvent] = Field(default_factory=list)
    degraded_roles: list[str] = Field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        return sum(len(o.evidence) for o in self.analyst_outputs.values())
