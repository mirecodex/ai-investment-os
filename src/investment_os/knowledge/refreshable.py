"""Hot-swappable knowledge base for long-running processes.

The bot process holds one ``RefreshableKnowledgeBase``; a scheduler job
rebuilds the inner KB from live feeds and swaps it atomically. Readers always
see a complete snapshot — never a half-loaded one. A failed refresh keeps the
previous KB serving (stale beats broken; staleness is what R2 gating and the
freshness factor are for).
"""

from __future__ import annotations

from investment_os.domain import MacroSnapshot
from investment_os.knowledge.ports import CuratedNews, KnowledgeBase, MarketSnapshot, TickerProfile


class RefreshableKnowledgeBase:
    def __init__(self, inner: KnowledgeBase) -> None:
        self._inner = inner

    def swap(self, new_inner: KnowledgeBase) -> None:
        self._inner = new_inner

    def list_tickers(self) -> list[TickerProfile]:
        return self._inner.list_tickers()

    def snapshot(self, ticker: str) -> MarketSnapshot | None:
        return self._inner.snapshot(ticker)

    def market_overview(self) -> tuple[float, float, list[CuratedNews]]:
        return self._inner.market_overview()

    def macro(self) -> MacroSnapshot:
        return self._inner.macro()

    def add_news(self, items: list[CuratedNews]) -> None:
        self._inner.add_news(items)
