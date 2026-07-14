from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field


def _labels_key(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(labels.items()))


@dataclass
class _Timing:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def observe(self, ms: float) -> None:
        self.count += 1
        self.total_ms += ms
        self.max_ms = max(self.max_ms, ms)


@dataclass
class MetricsRegistry:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    _timings: dict[tuple[str, tuple[tuple[str, str], ...]], _Timing] = field(default_factory=dict)

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[(name, _labels_key(labels))] += value

    def observe_ms(self, name: str, ms: float, **labels: str) -> None:
        key = (name, _labels_key(labels))
        with self._lock:
            timing = self._timings.setdefault(key, _Timing())
            timing.observe(ms)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            flat: dict[str, float] = {}
            for (name, labels), value in self._counters.items():
                flat[_render(name, labels)] = value
            for (name, labels), timing in self._timings.items():
                if timing.count:
                    flat[_render(name + "_avg_ms", labels)] = timing.total_ms / timing.count
                    flat[_render(name + "_max_ms", labels)] = timing.max_ms
            return flat


def _render(name: str, labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return name
    rendered = ",".join(f"{k}={v}" for k, v in labels)
    return f"{name}{{{rendered}}}"


metrics = MetricsRegistry()
