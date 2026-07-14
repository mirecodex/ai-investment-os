"""Confidence engine.

Implements the factor model from docs/fase-2-ai-architecture/08-confidence-engine.md:

    confidence = calibrate(
        w1*evidence_strength + w2*freshness + w3*analyst_agreement
        - w4*rule_conflict + w5*source_quality
    )

Factor construction:
- evidence_strength saturates (1 - exp(-Σreliability/k)): the tenth citation
  is worth less than the second, and unreliable sources barely count.
- freshness is a reliability-weighted exponential decay by evidence age.
- agreement penalizes dispersion of confidence-weighted analyst scores.
- calibration is a monotone piecewise-linear map, identity until backtesting
  data exists to fit it (docs/fase-5).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from itertools import pairwise

from investment_os.domain import AnalystOpinion, EvidenceRef

LOW_BAND = 0.45
HIGH_BAND = 0.70


@dataclass(frozen=True)
class ConfidenceWeights:
    evidence_strength: float = 0.30
    freshness: float = 0.20
    agreement: float = 0.25
    source_quality: float = 0.25
    rule_conflict_penalty: float = 0.12


@dataclass(frozen=True)
class ConfidenceBreakdown:
    evidence_strength: float
    freshness: float
    agreement: float
    source_quality: float
    rule_conflicts: int
    raw: float
    calibrated: float

    @property
    def band(self) -> str:
        if self.calibrated < LOW_BAND:
            return "LOW"
        if self.calibrated < HIGH_BAND:
            return "MEDIUM"
        return "HIGH"


@dataclass
class ConfidenceEngine:
    weights: ConfidenceWeights = field(default_factory=ConfidenceWeights)
    freshness_half_life_days: float = 5.0
    evidence_saturation: float = 3.0
    # Monotone (x, y) anchors; identity until fit against realized outcomes.
    calibration_points: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))

    def score(
        self,
        opinions: dict[str, AnalystOpinion],
        *,
        now: dt.datetime,
        rule_conflicts: int = 0,
    ) -> ConfidenceBreakdown:
        evidence = [ref for o in opinions.values() for ref in o.evidence]

        strength = self._evidence_strength(evidence)
        freshness = self._freshness(evidence, now)
        agreement = self._agreement(opinions)
        quality = self._source_quality(evidence)

        w = self.weights
        raw = (
            w.evidence_strength * strength
            + w.freshness * freshness
            + w.agreement * agreement
            + w.source_quality * quality
            - w.rule_conflict_penalty * rule_conflicts
        )
        raw = max(0.0, min(1.0, raw))
        return ConfidenceBreakdown(
            evidence_strength=round(strength, 4),
            freshness=round(freshness, 4),
            agreement=round(agreement, 4),
            source_quality=round(quality, 4),
            rule_conflicts=rule_conflicts,
            raw=round(raw, 4),
            calibrated=round(self._calibrate(raw), 4),
        )

    def _evidence_strength(self, evidence: list[EvidenceRef]) -> float:
        total = sum(ref.reliability for ref in evidence)
        return 1.0 - math.exp(-total / self.evidence_saturation)

    def _freshness(self, evidence: list[EvidenceRef], now: dt.datetime) -> float:
        if not evidence:
            return 0.0
        weighted = 0.0
        total = 0.0
        for ref in evidence:
            decay = math.pow(0.5, ref.age_days(now) / self.freshness_half_life_days)
            weighted += decay * ref.reliability
            total += ref.reliability
        return weighted / total if total > 0 else 0.0

    def _agreement(self, opinions: dict[str, AnalystOpinion]) -> float:
        if len(opinions) < 2:
            return 0.5  # a lone voice is neither consensus nor conflict
        weights = [o.confidence for o in opinions.values()]
        scores = [o.score for o in opinions.values()]
        total = sum(weights)
        if total <= 0:
            return 0.5
        mean = sum(s * w for s, w in zip(scores, weights, strict=True)) / total
        variance = sum(w * (s - mean) ** 2 for s, w in zip(scores, weights, strict=True)) / total
        # scores live in [-1, 1]; std of 1.0 ≈ full-blown disagreement
        return max(0.0, 1.0 - math.sqrt(variance))

    def _source_quality(self, evidence: list[EvidenceRef]) -> float:
        if not evidence:
            return 0.0
        return sum(ref.reliability for ref in evidence) / len(evidence)

    def _calibrate(self, raw: float) -> float:
        points = self.calibration_points
        if raw <= points[0][0]:
            return points[0][1]
        for (x0, y0), (x1, y1) in pairwise(points):
            if raw <= x1:
                if x1 == x0:
                    return y1
                t = (raw - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return points[-1][1]
