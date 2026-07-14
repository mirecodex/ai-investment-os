"""Shared domain types.

Schemas follow docs/fase-2-ai-architecture (agent specifications, LangGraph
state) and docs/fase-3-data-platform/07-database-vector-schema.md. Everything
that crosses an agent or interface boundary is a validated model, never a
loose dict.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field


class Stance(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"

    @classmethod
    def from_score(cls, score: float, band: float = 0.15) -> Stance:
        if score > band:
            return cls.POSITIVE
        if score < -band:
            return cls.NEGATIVE
        return cls.NEUTRAL


class Verdict(StrEnum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    ABSTAIN = "ABSTAIN"

    @property
    def bullishness(self) -> int:
        return {Verdict.SELL: -1, Verdict.HOLD: 0, Verdict.ABSTAIN: 0, Verdict.BUY: 1}[self]


class FlowRegime(StrEnum):
    HEAVY_SELL = "HEAVY_SELL"
    SELL = "SELL"
    BALANCED = "BALANCED"
    BUY = "BUY"
    HEAVY_BUY = "HEAVY_BUY"


class Side(StrEnum):
    BULL = "BULL"
    BEAR = "BEAR"


class EvidenceRef(BaseModel):
    """Citation-ready pointer into the knowledge base (never raw source text)."""

    source: str
    ref_id: str
    summary: str
    published_at: dt.datetime
    reliability: float = Field(ge=0.0, le=1.0)
    url: str | None = None

    def age_days(self, now: dt.datetime) -> float:
        return max(0.0, (now - self.published_at).total_seconds() / 86400.0)


class AnalystOpinion(BaseModel):
    role: str
    stance: Stance
    score: float = Field(ge=-1.0, le=1.0)
    key_points: list[str]
    evidence: list[EvidenceRef]
    confidence: float = Field(ge=0.0, le=1.0)
    caveats: list[str] = Field(default_factory=list)
    # Machine-readable side channel for the rule engine (e.g. flow_regime),
    # so rules never parse human-readable text.
    signals: dict[str, str] = Field(default_factory=dict)


class ArgumentPoint(BaseModel):
    claim: str
    weight: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceRef]


class Argument(BaseModel):
    side: Side
    points: list[ArgumentPoint]

    @property
    def strength(self) -> float:
        return sum(p.weight for p in self.points)


class RuleTrigger(BaseModel):
    rule_id: str
    reason: str
    effect: str


class Decision(BaseModel):
    verdict: Verdict
    proposed_verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: str
    reasons: list[str]
    triggered_rules: list[RuleTrigger] = Field(default_factory=list)
    requires_review: bool = False


class MacroSnapshot(BaseModel):
    bi_rate_pct: float
    usd_idr: float
    commodities: dict[str, float] = Field(default_factory=dict)


class MarketBrief(BaseModel):
    date: dt.date
    sentiment: Stance
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    index_change_pct: float
    net_foreign_flow_bn_idr: float
    highlights: list[str]
    macro: MacroSnapshot


class AuditEvent(BaseModel):
    node: str
    at: dt.datetime
    duration_ms: float
    note: str
