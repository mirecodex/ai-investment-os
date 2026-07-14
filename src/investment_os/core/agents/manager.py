from __future__ import annotations

from dataclasses import dataclass

from investment_os.core.agents.base import Analyst
from investment_os.knowledge.ports import MarketSnapshot


@dataclass(frozen=True)
class RoutingDecision:
    selected: list[str]
    skipped: list[str]
    note: str

    @property
    def has_quorum(self) -> bool:
        return len(self.selected) >= 2


class ResearchManager:
    def __init__(self, analysts: list[Analyst], *, min_committee: int = 2) -> None:
        self._analysts = analysts
        self._min_committee = min_committee

    def route(self, snapshot: MarketSnapshot) -> RoutingDecision:
        selected = [a.role for a in self._analysts if a.is_relevant(snapshot)]
        skipped = [a.role for a in self._analysts if a.role not in selected]

        note = f"selected: {', '.join(selected) or 'none'}"
        if skipped:
            note += f" · skipped: {', '.join(skipped)}"
        if len(selected) < self._min_committee:
            note += f" · di bawah kuorum ({self._min_committee})"

        return RoutingDecision(selected=selected, skipped=skipped, note=note)
