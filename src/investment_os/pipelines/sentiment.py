"""Interim lexicon-based sentiment for Indonesian financial headlines.

A stopgap so the news pipeline produces a usable signal before the LLM-backed
news-intelligence stage lands (docs/fase-3, doc 03). Deliberately shallow:
word-level polarity with a negation flip and square-root damping, tuned for
recall on headline vocabulary rather than nuance. The news analyst already
treats sentiment as one weighted input among many, so a coarse score is
acceptable here and calibration happens downstream.
"""

from __future__ import annotations

import re

_POSITIVE = frozenset(
    [
        "naik",
        "menguat",
        "tumbuh",
        "melonjak",
        "melesat",
        "melaju",
        "rekor",
        "laba",
        "untung",
        "surplus",
        "ekspansi",
        "akumulasi",
        "optimis",
        "positif",
        "membaik",
        "pulih",
        "dividen",
        "apresiasi",
        "kinerja",
        "solid",
        "kuat",
    ]
)

_NEGATIVE = frozenset(
    [
        "turun",
        "melemah",
        "anjlok",
        "merosot",
        "koreksi",
        "rugi",
        "defisit",
        "tekanan",
        "tertekan",
        "jual",
        "lesu",
        "khawatir",
        "negatif",
        "gagal",
        "pailit",
        "utang",
        "suspensi",
        "denda",
        "skandal",
        "boikot",
        "lemah",
    ]
)

_NEGATIONS = frozenset(["tidak", "tak", "bukan", "belum", "tanpa", "gagal"])

_WORD_RE = re.compile(r"[a-z]+")


def score_text(text: str) -> float:
    """Return sentiment in [-1, 1]; 0.0 when no polarity words are found."""
    words = _WORD_RE.findall(text.lower())
    positive = 0
    negative = 0
    for index, word in enumerate(words):
        negated = index > 0 and words[index - 1] in _NEGATIONS
        if word in _POSITIVE:
            positive, negative = (positive, negative + 1) if negated else (positive + 1, negative)
        elif word in _NEGATIVE:
            positive, negative = (positive + 1, negative) if negated else (positive, negative + 1)

    total = positive + negative
    if total == 0:
        return 0.0
    polarity = (positive - negative) / total
    # Damp low-evidence scores: one hit is worth half strength, many hits
    # approach full polarity asymptotically.
    damping = 1.0 - 1.0 / (total + 1)
    return round(polarity * damping, 4)
