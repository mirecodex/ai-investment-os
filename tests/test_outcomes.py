from __future__ import annotations

import bisect
import datetime as dt
from pathlib import Path

import pytest

from investment_os.core.agents import default_analysts
from investment_os.core.outcomes import OutcomeTracker
from investment_os.core.service import AnalysisService
from investment_os.data import Database, SqliteRecommendationStore
from investment_os.knowledge.fixtures import load_fixture_kb
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from tests.conftest import FIXTURE_PATH, NOW


async def store_with_recommendation(
    tmp_path: Path, *, age_days: int
) -> tuple[InMemoryKnowledgeBase, Database, SqliteRecommendationStore]:
    kb = load_fixture_kb(FIXTURE_PATH)
    db = Database(tmp_path / "outcomes.db")
    store = SqliteRecommendationStore(db)
    past_view = kb.as_of_view(NOW - dt.timedelta(days=age_days))
    service = AnalysisService(past_view, analysts=default_analysts(), recommendation_store=store)
    await service.analyze("BBCA")
    return kb, db, store


async def test_matured_recommendation_gets_outcome(tmp_path: Path) -> None:
    kb, db, store = await store_with_recommendation(tmp_path, age_days=40)
    tracker = OutcomeTracker(kb, store, horizon_days=10)

    assert tracker.run(now=NOW) == 1

    pairs = store.calibration_pairs(horizon="10d")
    assert len(pairs) == 1
    confidence, actual, _verdict = pairs[0]
    assert 0.0 <= confidence <= 1.0
    assert -1.0 < actual < 5.0

    assert tracker.run(now=NOW) == 0  # idempotent: nothing left pending
    db.close()


async def test_unmatured_recommendation_stays_pending(tmp_path: Path) -> None:
    kb, db, store = await store_with_recommendation(tmp_path, age_days=2)
    tracker = OutcomeTracker(kb, store, horizon_days=10)

    assert tracker.run(now=NOW) == 0
    assert store.calibration_pairs(horizon="10d") == []
    db.close()


async def test_horizon_counts_trading_bars_like_backtest(tmp_path: Path) -> None:
    kb, db, store = await store_with_recommendation(tmp_path, age_days=40)
    OutcomeTracker(kb, store, horizon_days=10).run(now=NOW)

    ((_conf, actual, _verdict),) = store.calibration_pairs(horizon="10d")
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None
    dates = [bar.date for bar in snapshot.bars]
    entry_idx = bisect.bisect_right(dates, (NOW - dt.timedelta(days=40)).date()) - 1
    expected = snapshot.bars[entry_idx + 10].close / snapshot.bars[entry_idx].close - 1.0
    assert actual == pytest.approx(expected)
    db.close()


async def test_missing_ticker_history_is_skipped_not_recorded(tmp_path: Path) -> None:
    kb, db, store = await store_with_recommendation(tmp_path, age_days=40)
    empty_kb = InMemoryKnowledgeBase(as_of=NOW, macro=kb.macro())
    tracker = OutcomeTracker(empty_kb, store, horizon_days=10)

    assert tracker.run(now=NOW) == 0  # no bars -> stays pending, no bogus data
    assert store.calibration_pairs(horizon="10d") == []
    db.close()
