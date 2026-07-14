"""Direction accuracy and confidence calibration from recorded outcomes.

Implements the metrics in docs/fase-5 (backtesting + evaluation): per-bucket
hit rate against confidence, and an expected calibration error (ECE). Reads
the (confidence, actual_return, verdict) triples accumulated by the
recommendation store — the longer the system runs, the sharper this gets.
"""

from __future__ import annotations

from dataclasses import dataclass

from investment_os.domain import Verdict


@dataclass(frozen=True)
class Bucket:
    low: float
    high: float
    count: int
    avg_confidence: float
    hit_rate: float


@dataclass(frozen=True)
class ReliabilityReport:
    horizon: str
    directional_count: int
    overall_hit_rate: float | None
    ece: float | None
    buckets: list[Bucket]


def _is_hit(verdict: Verdict, actual_return: float) -> bool | None:
    """Direction hit for actionable calls; HOLD/ABSTAIN carry no direction."""
    if verdict is Verdict.BUY:
        return actual_return > 0
    if verdict is Verdict.SELL:
        return actual_return < 0
    return None


def reliability_report(
    outcomes: list[tuple[float, float, Verdict]],
    *,
    horizon: str,
    bucket_count: int = 5,
) -> ReliabilityReport:
    directional = [
        (confidence, hit)
        for confidence, actual_return, verdict in outcomes
        if (hit := _is_hit(verdict, actual_return)) is not None
    ]
    if not directional:
        return ReliabilityReport(
            horizon=horizon, directional_count=0, overall_hit_rate=None, ece=None, buckets=[]
        )

    buckets: list[Bucket] = []
    ece_accumulator = 0.0
    width = 1.0 / bucket_count
    for index in range(bucket_count):
        low = index * width
        high = low + width
        members = [
            (confidence, hit)
            for confidence, hit in directional
            if low <= confidence < high or (index == bucket_count - 1 and confidence == 1.0)
        ]
        if not members:
            continue
        avg_confidence = sum(c for c, _ in members) / len(members)
        hit_rate = sum(1 for _, hit in members if hit) / len(members)
        ece_accumulator += (len(members) / len(directional)) * abs(avg_confidence - hit_rate)
        buckets.append(
            Bucket(
                low=round(low, 2),
                high=round(high, 2),
                count=len(members),
                avg_confidence=round(avg_confidence, 4),
                hit_rate=round(hit_rate, 4),
            )
        )

    overall = sum(1 for _, hit in directional if hit) / len(directional)
    return ReliabilityReport(
        horizon=horizon,
        directional_count=len(directional),
        overall_hit_rate=round(overall, 4),
        ece=round(ece_accumulator, 4),
        buckets=buckets,
    )
