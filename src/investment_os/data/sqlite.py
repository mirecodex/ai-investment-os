from __future__ import annotations

import builtins
import datetime as dt
import json

from investment_os.core.alerts import AlertState
from investment_os.core.explain import AnalysisReport
from investment_os.core.ports import RecommendationRecord
from investment_os.data.db import Database
from investment_os.domain import Verdict
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


class SqliteRecommendationStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(
        self,
        report: AnalysisReport,
        *,
        run_id: str,
        engine_version: str,
        as_of: dt.datetime,
    ) -> int:
        decision = report.decision
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recommendations (
                    run_id, ticker, company, sector, verdict, proposed_verdict,
                    confidence, confidence_band, requires_review, headline,
                    reasons_json, factors_json, audit_json,
                    engine_version, as_of, created_at,
                    narrative, llm_version, prompt_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    report.ticker,
                    report.company,
                    report.sector,
                    decision.verdict.value,
                    decision.proposed_verdict.value,
                    decision.confidence,
                    decision.confidence_band,
                    int(decision.requires_review),
                    report.headline,
                    json.dumps(decision.reasons, ensure_ascii=False),
                    json.dumps(report.confidence_factors),
                    json.dumps(
                        [event.model_dump(mode="json") for event in report.audit_trail],
                        ensure_ascii=False,
                    ),
                    engine_version,
                    as_of.isoformat(),
                    dt.datetime.now(tz=dt.UTC).isoformat(),
                    report.narrative,
                    report.llm_version,
                    report.prompt_version,
                ),
            )
            rec_id = cursor.lastrowid
            assert rec_id is not None

            conn.executemany(
                """
                INSERT INTO evidence_refs
                    (rec_id, source, ref_id, summary, published_at, reliability, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        rec_id,
                        ref.source,
                        ref.ref_id,
                        ref.summary,
                        ref.published_at.isoformat(),
                        ref.reliability,
                        ref.url,
                    )
                    for ref in report.evidence
                ],
            )
            conn.executemany(
                "INSERT INTO rule_triggers (rec_id, rule_id, effect, reason) VALUES (?, ?, ?, ?)",
                [
                    (rec_id, trigger.rule_id, trigger.effect, trigger.reason)
                    for trigger in decision.triggered_rules
                ],
            )

        metrics.increment("recommendations_stored")
        return rec_id

    def history(self, ticker: str | None = None, *, limit: int = 20) -> list[RecommendationRecord]:
        query = """
            SELECT r.*,
                   (SELECT group_concat(t.rule_id) FROM rule_triggers t WHERE t.rec_id = r.id)
                       AS rule_ids
            FROM recommendations r
        """
        params: list[object] = []
        if ticker is not None:
            query += " WHERE r.ticker = ?"
            params.append(ticker.upper())
        query += " ORDER BY r.created_at DESC, r.id DESC LIMIT ?"
        params.append(limit)

        with self._db.transaction() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            RecommendationRecord(
                id=row["id"],
                run_id=row["run_id"],
                ticker=row["ticker"],
                verdict=Verdict(row["verdict"]),
                proposed_verdict=Verdict(row["proposed_verdict"]),
                confidence=row["confidence"],
                confidence_band=row["confidence_band"],
                requires_review=bool(row["requires_review"]),
                headline=row["headline"],
                engine_version=row["engine_version"],
                triggered_rule_ids=row["rule_ids"].split(",") if row["rule_ids"] else [],
                created_at=dt.datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def record_outcome(
        self,
        rec_id: int,
        *,
        horizon: str,
        actual_return: float,
        evaluated_at: dt.datetime,
    ) -> None:
        with self._db.transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM recommendations WHERE id = ?", (rec_id,)
            ).fetchone()
            if exists is None:
                raise LookupError(f"recommendation {rec_id} tidak ditemukan")
            conn.execute(
                """
                INSERT INTO outcomes (rec_id, horizon, actual_return, evaluated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (rec_id, horizon) DO UPDATE SET
                    actual_return = excluded.actual_return,
                    evaluated_at = excluded.evaluated_at
                """,
                (rec_id, horizon, actual_return, evaluated_at.isoformat()),
            )

    def pending_outcomes(
        self, *, horizon: str, as_of_before: dt.datetime
    ) -> list[tuple[int, str, dt.datetime]]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.ticker, r.as_of
                FROM recommendations r
                LEFT JOIN outcomes o ON o.rec_id = r.id AND o.horizon = ?
                WHERE o.rec_id IS NULL AND r.as_of <= ?
                ORDER BY r.as_of
                """,
                (horizon, as_of_before.isoformat()),
            ).fetchall()
        return [(row["id"], row["ticker"], dt.datetime.fromisoformat(row["as_of"])) for row in rows]

    def calibration_pairs(self, *, horizon: str) -> list[tuple[float, float, Verdict]]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                """
                SELECT r.confidence, o.actual_return, r.verdict
                FROM outcomes o
                JOIN recommendations r ON r.id = o.rec_id
                WHERE o.horizon = ?
                ORDER BY o.evaluated_at
                """,
                (horizon,),
            ).fetchall()
        return [(row["confidence"], row["actual_return"], Verdict(row["verdict"])) for row in rows]


class SqliteSubscriptions:
    def __init__(self, db: Database) -> None:
        self._db = db

    def subscribe(self, user_id: str, chat_id: int) -> bool:
        now = dt.datetime.now(tz=dt.UTC).isoformat()
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
                (user_id, now),
            )
            cursor = conn.execute(
                "INSERT OR IGNORE INTO subscriptions (user_id, chat_id, created_at)"
                " VALUES (?, ?, ?)",
                (user_id, chat_id, now),
            )
        return cursor.rowcount > 0

    def unsubscribe(self, user_id: str) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        return cursor.rowcount > 0

    def unsubscribe_chat(self, chat_id: int) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM subscriptions WHERE chat_id = ?", (chat_id,))
        return cursor.rowcount > 0

    def chat_ids(self) -> list[int]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT chat_id FROM subscriptions ORDER BY created_at").fetchall()
        return [row["chat_id"] for row in rows]


class SqliteWatchlist:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list(self, user_id: str) -> list[str]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY created_at, ticker",
                (user_id,),
            ).fetchall()
        return [row["ticker"] for row in rows]

    def add(self, user_id: str, ticker: str) -> bool:
        symbol = ticker.strip().upper()
        if not symbol:
            return False
        now = dt.datetime.now(tz=dt.UTC).isoformat()
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
                (user_id, now),
            )
            cursor = conn.execute(
                "INSERT OR IGNORE INTO watchlist (user_id, ticker, created_at) VALUES (?, ?, ?)",
                (user_id, symbol, now),
            )
        return cursor.rowcount > 0

    def remove(self, user_id: str, ticker: str) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
                (user_id, ticker.strip().upper()),
            )
        return cursor.rowcount > 0

    def all_watchers(self) -> builtins.list[tuple[str, str]]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT user_id, ticker FROM watchlist ORDER BY ticker").fetchall()
        return [(row["user_id"], row["ticker"]) for row in rows]


class SqliteAlertState:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, ticker: str) -> AlertState | None:
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM alert_state WHERE ticker = ?", (ticker.upper(),)
            ).fetchone()
        if row is None:
            return None
        return AlertState(
            ticker=row["ticker"],
            verdict=Verdict(row["verdict"]),
            rule_ids=row["rule_ids"].split(",") if row["rule_ids"] else [],
            confidence_band=row["confidence_band"],
            updated_at=dt.datetime.fromisoformat(row["updated_at"]),
            event_ids=row["event_ids"].split(",") if row["event_ids"] else [],
        )

    def save(self, state: AlertState) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO alert_state
                    (ticker, verdict, rule_ids, confidence_band, updated_at, event_ids)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (ticker) DO UPDATE SET
                    verdict = excluded.verdict,
                    rule_ids = excluded.rule_ids,
                    confidence_band = excluded.confidence_band,
                    updated_at = excluded.updated_at,
                    event_ids = excluded.event_ids
                """,
                (
                    state.ticker.upper(),
                    state.verdict.value,
                    ",".join(state.rule_ids),
                    state.confidence_band,
                    state.updated_at.isoformat(),
                    ",".join(state.event_ids),
                ),
            )
