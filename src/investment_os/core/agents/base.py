from __future__ import annotations

from typing import Protocol, runtime_checkable

from investment_os.domain import AnalystOpinion, MarketBrief
from investment_os.knowledge.ports import MarketSnapshot


class AnalystError(RuntimeError):
    pass


@runtime_checkable
class Analyst(Protocol):
    role: str
    weight: float

    def is_relevant(self, snapshot: MarketSnapshot) -> bool: ...

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion: ...
