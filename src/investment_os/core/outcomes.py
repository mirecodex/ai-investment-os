from __future__ import annotations

import bisect
import datetime as dt

from investment_os.core.ports import RecommendationStore
from investment_os.knowledge.ports import KnowledgeBase
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


class OutcomeTracker:
    """Closes the calibration loop: once enough trading bars exist after a
    recommendation, the realized return over the horizon is recorded so
    `calibration_pairs` reflects real performance instead of manual entry.

    Horizons count trading bars, matching the backtester. A recommendation
    stays pending until the exit bar exists — never partially evaluated.
    """

    def __init__(
        self, kb: KnowledgeBase, store: RecommendationStore, *, horizon_days: int = 20
    ) -> None:
        self._kb = kb
        self._store = store
        self._horizon_days = horizon_days
        self._horizon = f"{horizon_days}d"

    def run(self, *, now: dt.datetime | None = None) -> int:
        now = now or dt.datetime.now(tz=dt.UTC)
        # Trading bars >= calendar days, so anything younger than horizon_days
        # calendar days cannot have an exit bar yet — cheap DB-side prefilter.
        cutoff = now - dt.timedelta(days=self._horizon_days)
        recorded = 0
        skipped = 0

        for rec_id, ticker, as_of in self._store.pending_outcomes(
            horizon=self._horizon, as_of_before=cutoff
        ):
            actual = self._realized_return(ticker, as_of.date())
            if actual is None:
                skipped += 1
                continue
            self._store.record_outcome(
                rec_id, horizon=self._horizon, actual_return=actual, evaluated_at=now
            )
            recorded += 1

        if recorded or skipped:
            metrics.increment("outcomes_recorded", value=float(recorded))
            log.info(
                "outcome_sweep_done", horizon=self._horizon, recorded=recorded, pending=skipped
            )
        return recorded

    def _realized_return(self, ticker: str, entry_date: dt.date) -> float | None:
        snapshot = self._kb.snapshot(ticker)
        if snapshot is None or not snapshot.bars:
            return None
        dates = [bar.date for bar in snapshot.bars]
        entry_idx = bisect.bisect_right(dates, entry_date) - 1
        if entry_idx < 0:
            return None
        exit_idx = entry_idx + self._horizon_days
        if exit_idx >= len(snapshot.bars):
            return None  # horizon not elapsed yet — stays pending
        entry = snapshot.bars[entry_idx].close
        exit_ = snapshot.bars[exit_idx].close
        return exit_ / entry - 1.0 if entry > 0 else None
