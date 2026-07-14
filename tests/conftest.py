from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from investment_os.app.container import Container, build_container
from investment_os.config import Settings
from investment_os.domain import AnalystOpinion, EvidenceRef, Stance

NOW = dt.datetime(2026, 7, 13, 2, 0, tzinfo=dt.UTC)
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "idx_demo.json"


def make_evidence(
    *,
    age_days: float = 1.0,
    reliability: float = 0.9,
    source: str = "test-source",
    ref_id: str = "ref-1",
) -> EvidenceRef:
    return EvidenceRef(
        source=source,
        ref_id=ref_id,
        summary="ringkasan bukti",
        published_at=NOW - dt.timedelta(days=age_days),
        reliability=reliability,
    )


def make_opinion(
    role: str,
    score: float,
    *,
    confidence: float = 0.8,
    evidence_count: int = 2,
    age_days: float = 1.0,
    reliability: float = 0.9,
    signals: dict[str, str] | None = None,
) -> AnalystOpinion:
    return AnalystOpinion(
        role=role,
        stance=Stance.from_score(score),
        score=score,
        key_points=[f"{role} point"],
        evidence=[
            make_evidence(age_days=age_days, reliability=reliability, ref_id=f"{role}-{i}")
            for i in range(evidence_count)
        ],
        confidence=confidence,
        signals=signals or {},
    )


@pytest.fixture(scope="session")
def container() -> Container:
    settings = Settings(fixtures_path=FIXTURE_PATH, telegram_bot_token=None)
    return build_container(settings)
