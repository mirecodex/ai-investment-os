from __future__ import annotations

import json
import re

from investment_os.domain import AnalystOpinion, Stance
from investment_os.knowledge.ports import CuratedNews

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_MAX_CONFIDENCE = 0.9


def parse_grounded_opinion(
    role: str,
    text: str,
    allowed: dict[str, CuratedNews],
    *,
    max_confidence: float = _MAX_CONFIDENCE,
) -> AnalystOpinion:
    """Validate an LLM reply into an opinion whose every citation exists.

    Raises ValueError on anything less than a fully grounded, in-range reply —
    callers decide whether that means fallback or recusal.
    """
    match = _JSON_RE.search(text)
    if match is None:
        raise ValueError("respons tidak memuat JSON")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("JSON bukan objek")

    score = _number(payload, "score", low=-1.0, high=1.0)
    confidence = min(_number(payload, "confidence", low=0.0, high=1.0), max_confidence)

    key_points = _strings(payload.get("key_points"))[:5]
    if not key_points:
        raise ValueError("key_points kosong")

    cited = _strings(payload.get("evidence_refs"))
    if not cited:
        raise ValueError("tanpa sitasi evidence_refs")
    unknown = [ref for ref in cited if ref not in allowed]
    if unknown:
        raise ValueError(f"sitasi tidak dikenal: {unknown}")

    return AnalystOpinion(
        role=role,
        stance=Stance.from_score(score),
        score=score,
        key_points=key_points,
        evidence=[allowed[ref].as_evidence() for ref in dict.fromkeys(cited)][:5],
        confidence=confidence,
        caveats=_strings(payload.get("caveats"))[:3],
        signals={"engine": "llm"},
    )


def _number(payload: dict[str, object], key: str, *, low: float, high: float) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} bukan angka")
    if not low <= float(value) <= high:
        raise ValueError(f"{key} di luar rentang [{low}, {high}]: {value}")
    return float(value)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
