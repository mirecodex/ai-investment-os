from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from investment_os.domain import Verdict


class Expectation(BaseModel):
    verdict: Verdict
    proposed_verdict: Verdict | None = None
    rules_include: list[str] = Field(default_factory=list)
    rules_exclude: list[str] = Field(default_factory=list)
    confidence_min: float | None = None
    confidence_max: float | None = None
    band: str | None = None
    requires_review: bool | None = None
    min_evidence: int | None = None


class GoldenCase(BaseModel):
    name: str
    ticker: str
    rationale: str
    expect: Expectation


class GoldenSuite(BaseModel):
    fixture: str  # KB fixture path, relative to repo root
    cases: list[GoldenCase]

    @classmethod
    def load(cls, path: Path) -> GoldenSuite:
        return cls.model_validate(json.loads(path.read_text()))
