from __future__ import annotations

import builtins
from collections import defaultdict
from typing import Protocol


class WatchlistRepository(Protocol):
    def list(self, user_id: str) -> list[str]: ...

    def add(self, user_id: str, ticker: str) -> bool: ...

    def remove(self, user_id: str, ticker: str) -> bool: ...

    def all_watchers(self) -> builtins.list[tuple[str, str]]:
        """Every (user_id, ticker) pair — the alert job's work list."""
        ...


class InMemoryWatchlist:
    def __init__(self) -> None:
        self._items: dict[str, list[str]] = defaultdict(list)

    def list(self, user_id: str) -> list[str]:
        return list(self._items[user_id])

    def add(self, user_id: str, ticker: str) -> bool:
        symbol = ticker.strip().upper()
        if not symbol or symbol in self._items[user_id]:
            return False
        self._items[user_id].append(symbol)
        return True

    def remove(self, user_id: str, ticker: str) -> bool:
        symbol = ticker.strip().upper()
        if symbol not in self._items[user_id]:
            return False
        self._items[user_id].remove(symbol)
        return True

    def all_watchers(self) -> builtins.list[tuple[str, str]]:
        return [(user_id, ticker) for user_id, tickers in self._items.items() for ticker in tickers]
