"""Analyst contract.

The MVP ships deterministic, evidence-driven analysts computed from curated
knowledge-base records. An LLM-backed analyst implements the same protocol
behind the same schema (``AnalystOpinion``), so upgrading a role is a wiring
change in the container, never a change to the committee.
"""

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
