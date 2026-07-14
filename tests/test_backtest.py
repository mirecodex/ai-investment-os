from __future__ import annotations

import datetime as dt

from investment_os.eval import run_backtest
from investment_os.knowledge.fixtures import load_fixture_kb
from tests.conftest import FIXTURE_PATH, NOW


def kb():  # type: ignore[no-untyped-def]
    return load_fixture_kb(FIXTURE_PATH)


def test_as_of_view_has_no_lookahead() -> None:
    base = kb()
    cutoff = NOW - dt.timedelta(days=40)
    view = base.as_of_view(cutoff)

    full = base.snapshot("ANTM")
    past = view.snapshot("ANTM")
    assert full is not None and past is not None

    assert past.as_of == cutoff
    assert past.bars and past.bars[-1].date <= cutoff.date()
    assert len(past.bars) < len(full.bars)
    assert all(item.published_at <= cutoff for item in past.news)
    assert past.news == []  # all fixture news is < 4 days old
    assert past.index_bars and past.index_bars[-1].date <= cutoff.date()


def test_as_of_view_drops_unreported_fundamentals() -> None:
    base = kb()
    # BBCA fundamentals were reported ~75 days before NOW
    before_report = NOW - dt.timedelta(days=100)
    after_report = NOW - dt.timedelta(days=40)

    early = base.as_of_view(before_report).snapshot("BBCA")
    late = base.as_of_view(after_report).snapshot("BBCA")
    assert early is not None and late is not None
    assert early.fundamentals is None
    assert late.fundamentals is not None


async def test_backtest_replays_and_measures() -> None:
    result = await run_backtest(kb(), horizon_days=10, stride_days=10, min_history=60)

    assert result.sample_count > 10
    tickers = {sample.ticker for sample in result.samples}
    assert {"BBCA", "ANTM", "TLKM"} <= tickers
    assert "SIDO" not in tickers  # 30 bars < min_history: nothing to replay

    for sample in result.samples:
        assert 0.0 <= sample.confidence <= 1.0
        assert -1.0 < sample.forward_return < 5.0

    assert result.reliability.horizon == "10d"
    assert result.reliability.directional_count <= result.sample_count


async def test_backtest_is_deterministic() -> None:
    first = await run_backtest(kb(), horizon_days=10, stride_days=15, min_history=60)
    second = await run_backtest(kb(), horizon_days=10, stride_days=15, min_history=60)
    assert first.samples == second.samples
