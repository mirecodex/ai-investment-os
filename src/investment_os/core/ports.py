"""Persistence ports consumed by core.

Core writes through these protocols and never sees a driver. The schema they
imply follows docs/fase-3-data-platform/07-database-vector-schema.md; the
SQLite implementation lives in ``investment_os.data``.
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol

from pydantic import BaseModel

from investment_os.core.explain import AnalysisReport
from investment_os.domain import Verdict


class RecommendationRecord(BaseModel):
    id: int
    run_id: str
    ticker: str
    verdict: Verdict
    proposed_verdict: Verdict
    confidence: float
    confidence_band: str
    requires_review: bool
    headline: str
    engine_version: str
    triggered_rule_ids: list[str]
    created_at: dt.datetime


class RecommendationStore(Protocol):
    def save(
        self,
        report: AnalysisReport,
        *,
        run_id: str,
        engine_version: str,
        as_of: dt.datetime,
    ) -> int:
        """Persist a full recommendation (evidence + rule triggers included)."""
        ...

    def history(
        self, ticker: str | None = None, *, limit: int = 20
    ) -> list[RecommendationRecord]: ...

    def record_outcome(
        self,
        rec_id: int,
        *,
        horizon: str,
        actual_return: float,
        evaluated_at: dt.datetime,
    ) -> None:
        """Attach a realized return so confidence can be calibrated later."""
        ...

    def calibration_pairs(self, *, horizon: str) -> list[tuple[float, float]]:
        """(confidence, actual_return) pairs for reliability analysis."""
        ...
