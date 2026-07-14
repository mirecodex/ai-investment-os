"""The golden suite IS a test: any drift in committee behavior fails CI."""

from __future__ import annotations

from pathlib import Path

from investment_os.domain import Verdict
from investment_os.eval import GoldenSuite, reliability_report, run_suite
from investment_os.eval.golden import Expectation, GoldenCase

REPO_ROOT = Path(__file__).resolve().parents[1]


async def test_golden_suite_passes() -> None:
    suite = GoldenSuite.load(REPO_ROOT / "eval" / "golden" / "decisions.json")
    results = await run_suite(suite, repo_root=REPO_ROOT)

    report = "\n".join(
        f"[{'PASS' if r.passed else 'FAIL'}] {r.case.name}: {r.summary} {r.failures}"
        for r in results
    )
    assert all(r.passed for r in results), f"golden regression:\n{report}"
    assert len(results) == 4


async def test_runner_detects_regressions() -> None:
    """A deliberately wrong expectation must fail loudly, not silently pass."""
    suite = GoldenSuite(
        fixture="data/fixtures/idx_demo.json",
        cases=[
            GoldenCase(
                name="bbca-wrong-expectation",
                ticker="BBCA",
                rationale="sengaja salah",
                expect=Expectation(
                    verdict=Verdict.SELL,
                    rules_include=["R2"],
                    confidence_max=0.1,
                ),
            )
        ],
    )
    results = await run_suite(suite, repo_root=REPO_ROOT)
    assert not results[0].passed
    assert len(results[0].failures) == 3


def test_reliability_report_math() -> None:
    outcomes = [
        # (confidence, actual_return, verdict)
        (0.9, 0.05, Verdict.BUY),  # hit
        (0.9, 0.02, Verdict.BUY),  # hit
        (0.85, -0.01, Verdict.BUY),  # miss
        (0.3, -0.04, Verdict.SELL),  # hit
        (0.3, 0.06, Verdict.SELL),  # miss
        (0.5, 0.10, Verdict.HOLD),  # no direction — excluded
        (0.5, 0.10, Verdict.ABSTAIN),  # excluded
    ]
    report = reliability_report(outcomes, horizon="20d")

    assert report.directional_count == 5
    assert report.overall_hit_rate == 0.6
    high = next(b for b in report.buckets if b.low == 0.8)
    assert high.count == 3
    assert high.hit_rate == round(2 / 3, 4)
    low = next(b for b in report.buckets if b.low == 0.2)
    assert low.hit_rate == 0.5
    assert report.ece is not None and report.ece > 0


def test_reliability_report_empty() -> None:
    report = reliability_report([(0.5, 0.1, Verdict.HOLD)], horizon="20d")
    assert report.directional_count == 0
    assert report.overall_hit_rate is None
    assert report.buckets == []
