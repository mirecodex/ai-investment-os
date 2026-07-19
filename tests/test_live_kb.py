from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from investment_os.knowledge.live import UniverseConfig, build_live_kb
from investment_os.knowledge.ports import PriceBar
from investment_os.pipelines.market import PriceFeedError
from investment_os.pipelines.news import RawNewsItem
from tests.conftest import NOW

UNIVERSE_PATH = Path(__file__).resolve().parents[1] / "data" / "universe" / "lq45-demo.json"


class FakePriceFeed:
    def __init__(self, *, broken: set[str] | None = None) -> None:
        self._broken = broken or set()

    async def daily_bars(self, symbol: str, *, days: int) -> list[PriceBar]:
        if symbol in self._broken:
            raise PriceFeedError(f"{symbol} down")
        base = dt.date(2026, 3, 2)
        return [
            PriceBar(
                date=base + dt.timedelta(days=i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1e6,
            )
            for i in range(days)
        ]

    async def index_bars(self, *, days: int) -> list[PriceBar]:
        base = dt.date(2026, 3, 2)
        return [
            PriceBar(
                date=base + dt.timedelta(days=i),
                open=7000.0 + i,
                high=7010.0 + i,
                low=6990.0 + i,
                close=7005.0 + i,
                volume=1e9,
            )
            for i in range(days)
        ]

    async def index_change_pct(self) -> float:
        return 0.8


def universe() -> UniverseConfig:
    config = UniverseConfig.load(UNIVERSE_PATH)
    return config.model_copy(update={"tickers": config.tickers[:3]})


async def test_live_kb_registers_universe_and_news() -> None:
    news = [
        RawNewsItem(
            source="Kontan",
            title="Laba BCA tumbuh dua digit",
            body="Bank Central Asia mencatat laba naik.",
            published_at=NOW - dt.timedelta(hours=6),
            tickers=["BBCA"],
            sentiment=0.5,
        )
    ]
    kb = await build_live_kb(universe(), FakePriceFeed(), news, history_days=60, now=NOW)

    assert [p.ticker for p in kb.list_tickers()] == ["BBCA", "BBRI", "BMRI"]
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None
    assert len(snapshot.bars) == 60
    assert snapshot.fundamentals is None
    assert snapshot.news and snapshot.news[0].source == "Kontan"

    assert len(snapshot.index_bars) == 60
    index_change, _, _ = kb.market_overview()
    # Derived from the last two fake index closes, not the 0.8% stub method.
    expected = (7064.0 / 7063.0 - 1.0) * 100
    assert index_change == pytest.approx(expected)


async def test_dead_ticker_degrades_gracefully() -> None:
    kb = await build_live_kb(
        universe(), FakePriceFeed(broken={"BBRI"}), [], history_days=60, now=NOW
    )
    assert [p.ticker for p in kb.list_tickers()] == ["BBCA", "BMRI"]


async def test_committee_runs_on_live_shaped_data() -> None:
    """No fundamentals + no foreign flow: those analysts recuse, run still completes."""
    from investment_os.core.agents import (
        ForeignFlowAnalyst,
        FundamentalAnalyst,
        NewsAnalyst,
        TechnicalAnalyst,
    )
    from investment_os.core.service import AnalysisService

    kb = await build_live_kb(universe(), FakePriceFeed(), [], history_days=60, now=NOW)
    service = AnalysisService(
        kb,
        analysts=[TechnicalAnalyst(), FundamentalAnalyst(), NewsAnalyst(), ForeignFlowAnalyst()],
        min_evidence=1,
    )
    result = await service.analyze("BBCA")
    assert result.report.decision.verdict is not None

    route_note = result.report.audit_trail[1].note
    assert route_note.startswith("selected: technical")
    skipped = route_note.split("skipped:")[1]
    assert "fundamental" in skipped
    assert "foreign_flow" in skipped


FULL_UNIVERSE_PATH = Path(__file__).resolve().parents[1] / "data" / "universe" / "lq45.json"

KNOWN_SECTORS = {
    "Perbankan",
    "Telekomunikasi",
    "Teknologi",
    "Konsumer",
    "Farmasi",
    "Kesehatan",
    "Pertambangan",
    "Energi",
    "Perkebunan",
    "Otomotif & Konglomerasi",
    "Ritel",
    "Properti",
    "Infrastruktur",
    "Industri Dasar",
}


def test_full_lq45_universe_is_well_formed() -> None:
    universe = UniverseConfig.load(FULL_UNIVERSE_PATH)
    tickers = [spec.ticker for spec in universe.tickers]

    assert len(tickers) == 45
    assert len(set(tickers)) == 45
    assert tickers == sorted(tickers)  # alphabetical keeps rebalancing diffs readable
    for spec in universe.tickers:
        assert len(spec.ticker) == 4 and spec.ticker.isupper() and spec.ticker.isalpha()
        assert spec.name and spec.aliases
        assert spec.sector in KNOWN_SECTORS, f"{spec.ticker}: sector '{spec.sector}' asing"
    assert universe.feeds and universe.sources


def test_full_universe_tagger_matches_aliases_not_substrings() -> None:
    tagger = UniverseConfig.load(FULL_UNIVERSE_PATH).tagger()
    assert tagger.tag("Laba Antam melonjak; BCA menaikkan dividen") == ["ANTM", "BBCA"]
    assert tagger.tag("Pertambangan pasir tanpa emiten disebut") == []
    # "Astra" must not fire on unrelated words containing the substring
    assert "ASII" not in tagger.tag("astragalus adalah tanaman herbal")
