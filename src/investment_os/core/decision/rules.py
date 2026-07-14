"""Declarative business rules (hard constraints on the committee).

Catalog follows docs/fase-2-ai-architecture/07-decision-engine.md. Rules are
data: auditable, orderable by priority, and changeable without touching the
evaluator. The LLM (or heuristic committee) proposes; rules dispose.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from investment_os.domain import FlowRegime, Stance, Verdict


class EffectKind(StrEnum):
    FORCE = "FORCE"
    CAP_BULLISH = "CAP_BULLISH"
    FLAG_REVIEW = "FLAG_REVIEW"


@dataclass(frozen=True)
class Effect:
    kind: EffectKind
    verdict: Verdict | None = None


@dataclass(frozen=True)
class DecisionFacts:
    fundamental_stance: Stance | None
    fundamental_score: float
    news_stance: Stance | None
    flow_regime: FlowRegime | None
    evidence_count: int
    min_evidence: int
    data_stale: bool
    confidence: float
    low_confidence_threshold: float


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    priority: int  # lower runs first; FORCE at equal priority beats CAP
    applies: Callable[[DecisionFacts], bool]
    effect: Effect
    reason: str


def default_rules() -> list[Rule]:
    return [
        Rule(
            rule_id="R2",
            description="Evidence gating: bukti kurang atau data basi",
            priority=10,
            applies=lambda f: f.evidence_count < f.min_evidence or f.data_stale,
            effect=Effect(EffectKind.FORCE, Verdict.ABSTAIN),
            reason="Bukti tidak memadai untuk mengambil posisi.",
        ),
        Rule(
            rule_id="R1",
            description="Fundamental kuat vs sentimen & flow negatif",
            priority=20,
            applies=lambda f: (
                f.fundamental_stance is Stance.POSITIVE
                and f.fundamental_score >= 0.3
                and f.news_stance is Stance.NEGATIVE
                and f.flow_regime in (FlowRegime.HEAVY_SELL, FlowRegime.SELL)
            ),
            effect=Effect(EffectKind.FORCE, Verdict.HOLD),
            reason="Fundamental kuat, tetapi sentimen pasar masih negatif.",
        ),
        Rule(
            rule_id="R1b",
            description="Distribusi asing berat membatasi rekomendasi beli",
            priority=30,
            applies=lambda f: f.flow_regime is FlowRegime.HEAVY_SELL,
            effect=Effect(EffectKind.CAP_BULLISH, Verdict.HOLD),
            reason="Tekanan jual asing berat — tunggu stabilisasi flow.",
        ),
        Rule(
            rule_id="R3",
            description="Confidence floor",
            priority=40,
            applies=lambda f: f.confidence < f.low_confidence_threshold,
            effect=Effect(EffectKind.FLAG_REVIEW),
            reason="Confidence di bawah ambang — disarankan human review.",
        ),
    ]
