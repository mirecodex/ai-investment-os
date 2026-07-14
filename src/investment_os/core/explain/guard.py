"""Numeric guard: LLM text may not introduce financial figures.

Coding standard (docs/fase-6): "tidak ada angka finansial di-hardcode dari
LLM". Every number in generated narrative must already exist somewhere in the
evidence, key points, or decision data it was given. Numbers are compared as
normalized digit strings so ``9.200``, ``9,200`` and ``9200`` all match.
"""

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
