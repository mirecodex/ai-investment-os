from __future__ import annotations

import math
from collections.abc import Sequence


def sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    return sum(values[-window:]) / window


def rsi(closes: Sequence[float], period: int = 14) -> float | None:
    """Wilder's RSI over the trailing window."""
    if len(closes) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for prev, curr in zip(closes[-period - 1 : -1], closes[-period:], strict=True):
        delta = curr - prev
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - 100.0 / (1.0 + rs)


def zscore(values: Sequence[float], sample: float) -> float | None:
    if len(values) < 5:
        return None
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    std = math.sqrt(variance)
    if std < 1e-9:
        return 0.0
    return (sample - mean) / std


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
