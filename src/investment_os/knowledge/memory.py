"""In-memory knowledge base used for the offline demo and tests."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from investment_os.domain import MacroSnapshot
from investment_os.knowledge.ports import (
    CuratedNews,
    FundamentalSnapshot,
    MarketSnapshot,
    PriceBar,
    TickerProfile,
)


class InMemoryKnowledgeBase:
    def __init__(self, *, as_of: dt.datetime, macro: MacroSnapshot) -> None:
        self._as_of = as_of
        self._macro = macro
        self._profiles: dict[str, TickerProfile] = {}
        self._bars: dict[str, list[PriceBar]] = {}
        self._news: dict[str, list[CuratedNews]] = defaultdict(list)
        self._market_news: list[CuratedNews] = []
        self._fundamentals: dict[str, FundamentalSnapshot] = {}
        self._index_change_pct = 0.0
        self._index_bars: list[PriceBar] = []

    def register_ticker(
        self,
        profile: TickerProfile,
        bars: list[PriceBar],
        fundamentals: FundamentalSnapshot | None = None,
    ) -> None:
        symbol = profile.ticker.upper()
        self._profiles[symbol] = profile
        self._bars[symbol] = sorted(bars, key=lambda b: b.date)
        if fundamentals is not None:
            self._fundamentals[symbol] = fundamentals

    def set_index_change_pct(self, value: float) -> None:
        self._index_change_pct = value

    def set_index_bars(self, bars: list[PriceBar]) -> None:
        self._index_bars = sorted(bars, key=lambda b: b.date)

    def add_news(self, items: list[CuratedNews]) -> None:
        for item in items:
            if item.tickers:
                for symbol in item.tickers:
                    self._news[symbol.upper()].append(item)
            else:
                self._market_news.append(item)

    def list_tickers(self) -> list[TickerProfile]:
        return sorted(self._profiles.values(), key=lambda p: p.ticker)

    def snapshot(self, ticker: str) -> MarketSnapshot | None:
        symbol = ticker.upper()
        profile = self._profiles.get(symbol)
        if profile is None:
            return None
        news = sorted(self._news.get(symbol, []), key=lambda n: n.published_at, reverse=True)
        return MarketSnapshot(
            profile=profile,
            bars=self._bars.get(symbol, []),
            news=news,
            fundamentals=self._fundamentals.get(symbol),
            macro=self._macro,
            as_of=self._as_of,
            index_bars=self._index_bars,
            sector_returns=self._sector_returns(),
        )

    def _sector_returns(self, window: int = 20) -> dict[str, float]:
        """Average trailing return per sector across the whole universe."""
        per_sector: dict[str, list[float]] = defaultdict(list)
        for symbol, bars in self._bars.items():
            if len(bars) <= window:
                continue
            trailing = bars[-1].close / bars[-window - 1].close - 1.0
            per_sector[self._profiles[symbol].sector].append(trailing)
        return {sector: sum(returns) / len(returns) for sector, returns in per_sector.items()}

    def market_overview(self) -> tuple[float, float, list[CuratedNews]]:
        net_flow = 0.0
        for bars in self._bars.values():
            if bars:
                net_flow += bars[-1].net_foreign_bn_idr
        headlines = sorted(
            self._market_news + [n for items in self._news.values() for n in items],
            key=lambda n: n.importance,
            reverse=True,
        )
        return self._index_change_pct, net_flow, headlines[:5]

    def macro(self) -> MacroSnapshot:
        return self._macro
