from __future__ import annotations

import datetime as dt

import pytest

from investment_os.domain import Verdict
from investment_os.eval import BacktestSample, run_backtest, strategy_report
from investment_os.knowledge.fixtures import load_fixture_kb
from tests.conftest import FIXTURE_PATH


def sample(
    entry: str,
    exit_: str,
    ret: float,
    *,
    ticker: str = "AAAA",
    verdict: Verdict = Verdict.BUY,
) -> BacktestSample:
    return BacktestSample(
        ticker=ticker,
        as_of=dt.date.fromisoformat(entry),
        exit_date=dt.date.fromisoformat(exit_),
        verdict=verdict,
        confidence=0.7,
        forward_return=ret,
    )


def test_rounds_never_overlap_and_compound() -> None:
    report = strategy_report(
        [
            sample("2026-01-05", "2026-02-02", 0.10),
            sample("2026-01-19", "2026-02-16", 9.99),  # entry mid-round: capital busy, skipped
            sample("2026-02-02", "2026-03-02", -0.05),
        ]
    )
    assert [r.entry.isoformat() for r in report.rounds] == ["2026-01-05", "2026-02-02"]
    assert report.strategy_total == pytest.approx(1.10 * 0.95 - 1.0)
    assert report.max_drawdown == pytest.approx(0.05)
    assert report.index_total is None  # no index bars supplied


def test_same_day_buys_are_equal_weighted() -> None:
    report = strategy_report(
        [
            sample("2026-01-05", "2026-02-02", 0.20, ticker="AAAA"),
            sample("2026-01-05", "2026-02-02", -0.10, ticker="BBBB"),
            sample("2026-01-05", "2026-02-02", 0.50, ticker="CCCC", verdict=Verdict.HOLD),
        ]
    )
    assert report.round_count == 1
    assert report.rounds[0].positions == 2  # HOLD never enters the portfolio
    assert report.rounds[0].strategy_return == pytest.approx(0.05)


def test_no_buy_signals_yields_empty_report() -> None:
    report = strategy_report([sample("2026-01-05", "2026-02-02", 0.3, verdict=Verdict.SELL)])
    assert report.rounds == []
    assert report.strategy_total == 0.0
    assert report.index_total is None


async def test_fixture_backtest_produces_strategy_with_benchmark() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    result = await run_backtest(kb, horizon_days=10, stride_days=10, min_history=60)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None

    report = strategy_report(result.samples, snapshot.index_bars)

    assert report.round_count >= 1
    assert report.index_total is not None  # IHSG covered every window
    assert -1.0 < report.strategy_total < 10.0
    assert 0.0 <= report.max_drawdown < 1.0
    for first, second in zip(report.rounds, report.rounds[1:], strict=False):
        assert second.entry >= first.exit  # capital in one place at a time
