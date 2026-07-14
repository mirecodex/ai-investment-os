from __future__ import annotations

import datetime as dt

from investment_os.core.agents import default_analysts
from investment_os.core.agents.committee import consensus_score
from investment_os.core.agents.macro import MacroAnalyst
from investment_os.core.agents.manager import ResearchManager
from investment_os.core.agents.quant import QuantAnalyst
from investment_os.core.agents.sector import SectorRotationAnalyst
from investment_os.core.market_intel import MarketBriefBuilder
from investment_os.domain import MacroSnapshot, MarketBrief, Stance
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from investment_os.knowledge.ports import MarketSnapshot, PriceBar, TickerProfile
from tests.conftest import NOW, make_opinion

MACRO = MacroSnapshot(
    bi_rate_pct=6.0,
    usd_idr=15850,
    usd_idr_change_pct=1.0,
    commodities={"batu bara": 2.0, "nikel": 1.0},
)


def bars(days: int, *, start: float = 100.0, daily_pct: float = 0.0) -> list[PriceBar]:
    result = []
    price = start
    base = dt.date(2026, 2, 2)
    for i in range(days):
        # Deterministic wiggle so return series have nonzero variance.
        jitter = 0.002 if i % 2 == 0 else -0.0015
        close = price * (1 + daily_pct + jitter)
        result.append(
            PriceBar(
                date=base + dt.timedelta(days=i),
                open=price,
                high=max(price, close) * 1.005,
                low=min(price, close) * 0.995,
                close=close,
                volume=1e6,
            )
        )
        price = close
    return result


def snapshot(
    *,
    sector: str = "Pertambangan",
    ticker_bars: list[PriceBar] | None = None,
    index_bars: list[PriceBar] | None = None,
    sector_returns: dict[str, float] | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        profile=TickerProfile(ticker="TEST", name="Test Corp", sector=sector),
        bars=ticker_bars if ticker_bars is not None else bars(60, daily_pct=0.004),
        news=[],
        fundamentals=None,
        macro=MACRO,
        as_of=NOW,
        index_bars=index_bars or [],
        sector_returns=sector_returns or {},
    )


def brief() -> MarketBrief:
    return MarketBrief(
        date=NOW.date(),
        sentiment=Stance.NEUTRAL,
        score=0.0,
        confidence=0.5,
        index_change_pct=0.0,
        net_foreign_flow_bn_idr=0.0,
        highlights=[],
        macro=MACRO,
    )


# -- quant ------------------------------------------------------------------------


async def test_quant_rewards_steady_uptrend_and_computes_beta() -> None:
    snap = snapshot(
        ticker_bars=bars(60, daily_pct=0.004),
        index_bars=bars(60, start=7000, daily_pct=0.002),
    )
    opinion = await QuantAnalyst().assess(snap, brief())

    assert opinion.score > 0.3
    assert opinion.evidence and "beta" in opinion.evidence[0].summary
    assert any("Beta" in point for point in opinion.key_points)


async def test_quant_flags_high_volatility() -> None:
    wild = bars(60)
    for i, bar in enumerate(wild):
        factor = 1.06 if i % 2 == 0 else 0.95
        wild[i] = bar.model_copy(update={"close": bar.open * factor})
    opinion = await QuantAnalyst().assess(snapshot(ticker_bars=wild), brief())
    assert any("Volatilitas sangat tinggi" in c for c in opinion.caveats)


def test_quant_recuses_on_short_history() -> None:
    assert not QuantAnalyst().is_relevant(snapshot(ticker_bars=bars(30)))


# -- macro ------------------------------------------------------------------------


async def test_macro_favors_commodity_sector_on_strong_commodities() -> None:
    opinion = await MacroAnalyst().assess(snapshot(sector="Pertambangan"), brief())
    assert opinion.score > 0
    assert opinion.evidence[0].source == "macro"


async def test_macro_penalizes_importers_on_weak_rupiah() -> None:
    mining = await MacroAnalyst().assess(snapshot(sector="Pertambangan"), brief())
    consumer = await MacroAnalyst().assess(snapshot(sector="Konsumer"), brief())
    assert consumer.score < mining.score


# -- sector rotation ----------------------------------------------------------------


async def test_sector_rotation_scores_relative_strength() -> None:
    leader = await SectorRotationAnalyst().assess(
        snapshot(sector_returns={"Pertambangan": 0.06, "Perbankan": 0.01, "Konsumer": -0.02}),
        brief(),
    )
    laggard = await SectorRotationAnalyst().assess(
        snapshot(sector_returns={"Pertambangan": -0.04, "Perbankan": 0.03, "Konsumer": 0.02}),
        brief(),
    )
    assert leader.score > 0.3
    assert laggard.score < -0.3
    assert "peringkat 1/3" in leader.key_points[0]


def test_sector_rotation_recuses_without_cross_section() -> None:
    analyst = SectorRotationAnalyst()
    assert not analyst.is_relevant(snapshot(sector_returns={"Pertambangan": 0.05}))
    assert not analyst.is_relevant(snapshot(sector_returns={"Perbankan": 0.05, "Lain": 0.01}))


# -- research manager & consensus -----------------------------------------------------


def test_manager_routes_full_committee_and_reports_skips() -> None:
    manager = ResearchManager(default_analysts())
    decision = manager.route(snapshot(sector_returns={"Pertambangan": 0.05, "Perbankan": 0.01}))
    assert "technical" in decision.selected
    assert "quant" in decision.selected
    assert "fundamental" in decision.skipped  # no fundamentals in snapshot
    assert decision.has_quorum
    assert "skipped: " in decision.note


def test_manager_flags_missing_quorum() -> None:
    manager = ResearchManager(default_analysts())
    decision = manager.route(snapshot(ticker_bars=bars(10)))
    assert decision.selected == ["macro"]
    assert not decision.has_quorum
    assert "kuorum" in decision.note


def test_neutral_opinions_do_not_dilute_consensus() -> None:
    weights = {"a": 1.0, "b": 1.0, "n1": 1.0, "n2": 1.0, "n3": 1.0}
    directional = {
        "a": make_opinion("a", 0.6, confidence=0.9),
        "b": make_opinion("b", 0.5, confidence=0.8),
    }
    with_neutrals = directional | {
        "n1": make_opinion("n1", 0.02),
        "n2": make_opinion("n2", -0.05),
        "n3": make_opinion("n3", 0.0),
    }
    assert consensus_score(with_neutrals, weights) == consensus_score(directional, weights)


def test_sector_returns_computed_across_universe() -> None:
    kb = InMemoryKnowledgeBase(as_of=NOW, macro=MACRO)
    kb.register_ticker(
        TickerProfile(ticker="AAAA", name="A", sector="Pertambangan"),
        bars(40, daily_pct=0.005),
    )
    kb.register_ticker(
        TickerProfile(ticker="BBBB", name="B", sector="Perbankan"),
        bars(40, daily_pct=-0.002),
    )
    kb.set_index_bars(bars(40, start=7000))
    MarketBriefBuilder(kb)  # smoke: builder tolerates the extended KB

    snap = kb.snapshot("AAAA")
    assert snap is not None
    assert snap.sector_returns["Pertambangan"] > snap.sector_returns["Perbankan"]
    assert len(snap.index_bars) == 40
