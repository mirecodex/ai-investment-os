from __future__ import annotations

import pytest

from investment_os.core.confidence import ConfidenceEngine
from tests.conftest import NOW, make_opinion


def test_more_evidence_raises_confidence() -> None:
    engine = ConfidenceEngine()
    sparse = engine.score({"a": make_opinion("a", 0.5, evidence_count=1)}, now=NOW)
    rich = engine.score({"a": make_opinion("a", 0.5, evidence_count=6)}, now=NOW)
    assert rich.calibrated > sparse.calibrated


def test_stale_evidence_lowers_confidence() -> None:
    engine = ConfidenceEngine()
    fresh = engine.score({"a": make_opinion("a", 0.5, age_days=0.5)}, now=NOW)
    stale = engine.score({"a": make_opinion("a", 0.5, age_days=30.0)}, now=NOW)
    assert stale.freshness < fresh.freshness
    assert stale.calibrated < fresh.calibrated


def test_disagreement_lowers_confidence() -> None:
    engine = ConfidenceEngine()
    aligned = engine.score({"a": make_opinion("a", 0.6), "b": make_opinion("b", 0.5)}, now=NOW)
    split = engine.score({"a": make_opinion("a", 0.9), "b": make_opinion("b", -0.9)}, now=NOW)
    assert split.agreement < aligned.agreement
    assert split.calibrated < aligned.calibrated


def test_rule_conflicts_penalize() -> None:
    engine = ConfidenceEngine()
    opinions = {"a": make_opinion("a", 0.5), "b": make_opinion("b", 0.4)}
    calm = engine.score(opinions, now=NOW, rule_conflicts=0)
    conflicted = engine.score(opinions, now=NOW, rule_conflicts=2)
    assert conflicted.calibrated < calm.calibrated


def test_calibration_is_piecewise_linear() -> None:
    engine = ConfidenceEngine(calibration_points=((0.0, 0.0), (0.5, 0.3), (1.0, 1.0)))
    assert engine._calibrate(0.25) == pytest.approx(0.15)
    assert engine._calibrate(0.75) == pytest.approx(0.65)
    assert engine._calibrate(1.0) == pytest.approx(1.0)


def test_bands() -> None:
    engine = ConfidenceEngine()
    breakdown = engine.score(
        {"a": make_opinion("a", 0.5, evidence_count=5), "b": make_opinion("b", 0.5)},
        now=NOW,
    )
    assert breakdown.band in ("LOW", "MEDIUM", "HIGH")
    assert 0.0 <= breakdown.calibrated <= 1.0
