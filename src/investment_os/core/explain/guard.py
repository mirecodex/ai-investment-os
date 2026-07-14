from __future__ import annotations

import re
from collections.abc import Iterable

_NUMBER_RE = re.compile(r"\d[\d.,]*")

_BANNED_PHRASES = (
    "pasti naik",
    "pasti turun",
    "dijamin",
    "jaminan profit",
    "tidak mungkin rugi",
)


def _normalize(raw: str) -> str:
    digits = re.sub(r"[^\d]", "", raw)
    return digits.lstrip("0") or "0"


def extract_numbers(text: str) -> set[str]:
    return {_normalize(match) for match in _NUMBER_RE.findall(text)}


def narrative_violations(narrative: str, allowed_sources: Iterable[str]) -> list[str]:
    """Return reasons this narrative must be rejected (empty = clean)."""
    violations: list[str] = []

    allowed: set[str] = set()
    for source in allowed_sources:
        allowed |= extract_numbers(source)

    for number in sorted(extract_numbers(narrative) - allowed):
        violations.append(f"angka tidak bersumber: {number}")

    lowered = narrative.lower()
    for phrase in _BANNED_PHRASES:
        if phrase in lowered:
            violations.append(f"frasa terlarang: '{phrase}'")

    return violations
