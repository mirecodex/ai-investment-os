"""Knowledge base port.

Agents never read raw sources; they read curated records through this port
(docs/fase-2, principle 1). The protocol is the seam where Postgres/vector
implementations replace the in-memory store without touching core.
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol

from pydantic import BaseModel, Field

from investment_os.domain import EvidenceRef, MacroSnapshot


class TickerProfile(BaseModel):
    ticker: str
    name: str
    sector: str
    board: str = "Utama"


class PriceBar(BaseModel):
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: float
    net_foreign_bn_idr: float = 0.0


class CuratedNews(BaseModel):
    ref_id: str
    source: str
    title: str
    summary: str
    tickers: list[str]
    published_at: dt.datetime
    sentiment: float = Field(ge=-1.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    url: str | None = None

    def as_evidence(self) -> EvidenceRef:
        return EvidenceRef(
            source=self.source,
            ref_id=self.ref_id,
            summary=self.title,
            published_at=self.published_at,
            reliability=self.reliability,
            url=self.url,
        )


class FundamentalSnapshot(BaseModel):
    ticker: str
    period: str
    roe_pct: float
    net_margin_pct: float
    debt_to_equity: float
    pe_ratio: float
    sector_pe_ratio: float
    revenue_yoy_pct: float
    reported_at: dt.datetime
    source: str = "laporan-keuangan"

    def as_evidence(self) -> EvidenceRef:
        return EvidenceRef(
            source=self.source,
            ref_id=f"{self.ticker}-{self.period}",
            summary=(
                f"{self.ticker} {self.period}: ROE {self.roe_pct:.1f}%, "
                f"PER {self.pe_ratio:.1f}x (sektor {self.sector_pe_ratio:.1f}x), "
                f"DER {self.debt_to_equity:.2f}"
            ),
            published_at=self.reported_at,
            reliability=0.95,
        )


class MarketSnapshot(BaseModel):
    """Everything an analysis run may consume for one ticker, pre-curated."""

    profile: TickerProfile
    bars: list[PriceBar]
    news: list[CuratedNews]
    fundamentals: FundamentalSnapshot | None
    macro: MacroSnapshot
    as_of: dt.datetime


class KnowledgeBase(Protocol):
    def list_tickers(self) -> list[TickerProfile]: ...

    def snapshot(self, ticker: str) -> MarketSnapshot | None: ...

    def market_overview(self) -> tuple[float, float, list[CuratedNews]]:
        """Return (index_change_pct, net_foreign_flow_bn_idr, top market news)."""
        ...

    def macro(self) -> MacroSnapshot: ...

    def add_news(self, items: list[CuratedNews]) -> None: ...
