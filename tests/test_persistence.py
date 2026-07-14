from __future__ import annotations

from pathlib import Path

import pytest

from investment_os.app.container import Container
from investment_os.data import Database, SqliteRecommendationStore, SqliteWatchlist
from investment_os.domain import Verdict
from tests.conftest import NOW


async def test_analysis_is_persisted_with_rules_and_confidence(container: Container) -> None:
    result = await container.analysis.analyze("ANTM")

    records = container.recommendations.history("ANTM", limit=1)
    assert len(records) == 1
    record = records[0]
    assert record.verdict is Verdict.HOLD
    assert record.confidence == pytest.approx(result.report.decision.confidence)
    assert "R1" in record.triggered_rule_ids
    assert record.engine_version.startswith("heuristic-")


async def test_history_filters_by_ticker(container: Container) -> None:
    await container.analysis.analyze("BBCA")
    assert all(r.ticker == "BBCA" for r in container.recommendations.history("BBCA"))
    assert len(container.recommendations.history(limit=50)) >= 2


async def test_outcomes_feed_calibration_pairs(container: Container) -> None:
    await container.analysis.analyze("TLKM")
    record = container.recommendations.history("TLKM", limit=1)[0]

    container.recommendations.record_outcome(
        record.id, horizon="20d", actual_return=0.041, evaluated_at=NOW
    )
    # Re-evaluation of the same horizon overwrites, not duplicates.
    container.recommendations.record_outcome(
        record.id, horizon="20d", actual_return=0.052, evaluated_at=NOW
    )

    pairs = container.recommendations.calibration_pairs(horizon="20d")
    assert (record.confidence, 0.052) in pairs
    assert len([p for p in pairs if p[0] == record.confidence]) == 1


def test_outcome_for_unknown_recommendation_raises(container: Container) -> None:
    with pytest.raises(LookupError):
        container.recommendations.record_outcome(
            999_999, horizon="20d", actual_return=0.0, evaluated_at=NOW
        )


def test_watchlist_survives_reconnection(tmp_path: Path) -> None:
    db_path = tmp_path / "watchlist.db"

    first = Database(db_path)
    watchlist = SqliteWatchlist(first)
    assert watchlist.add("user-1", "bbca")
    assert not watchlist.add("user-1", "BBCA")
    first.close()

    second = Database(db_path)
    reopened = SqliteWatchlist(second)
    assert reopened.list("user-1") == ["BBCA"]
    assert reopened.remove("user-1", "BBCA")
    assert reopened.list("user-1") == []
    second.close()


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "migrate.db"
    Database(db_path).close()
    db = Database(db_path)
    store = SqliteRecommendationStore(db)
    assert store.history() == []
    assert store.calibration_pairs(horizon="20d") == []
    db.close()


async def test_stored_evidence_is_reconstructable(container: Container) -> None:
    await container.analysis.analyze("ANTM")
    with container.db.transaction() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM evidence_refs e
            JOIN recommendations r ON r.id = e.rec_id
            WHERE r.ticker = 'ANTM'
            """
        ).fetchone()
    assert row["n"] > 0

    with container.db.transaction() as conn:
        audit = conn.execute(
            "SELECT audit_json FROM recommendations WHERE ticker = 'ANTM' LIMIT 1"
        ).fetchone()
    assert "load_context" in audit["audit_json"]
