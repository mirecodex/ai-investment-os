from __future__ import annotations

import datetime as dt
from pathlib import Path

from investment_os.app.container import Container
from investment_os.core.alerts import (
    AlertService,
    AlertState,
    MarketEvent,
    market_events,
    material_changes,
)
from investment_os.data import Database, SqliteAlertState
from investment_os.domain import MacroSnapshot, Verdict
from investment_os.interfaces.telegram.presenter import render_alert
from investment_os.knowledge.ports import MarketSnapshot, PriceBar, TickerProfile
from investment_os.users import InMemoryWatchlist
from tests.conftest import NOW
from tests.test_new_analysts import bars


class MemoryAlertState:
    def __init__(self) -> None:
        self.states: dict[str, AlertState] = {}

    def get(self, ticker: str) -> AlertState | None:
        return self.states.get(ticker)

    def save(self, state: AlertState) -> None:
        self.states[state.ticker] = state


class CollectingSender:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
        self.sent.append((chat_id, text))


def state(verdict: Verdict, rules: list[str]) -> AlertState:
    return AlertState(
        ticker="BBCA", verdict=verdict, rule_ids=rules, confidence_band="HIGH", updated_at=NOW
    )


# -- material change detection ---------------------------------------------------


def test_first_observation_is_silent() -> None:
    assert material_changes(None, state(Verdict.BUY, [])) == []


def test_verdict_flip_is_material() -> None:
    changes = material_changes(state(Verdict.BUY, []), state(Verdict.HOLD, []))
    assert changes == ["keputusan berubah: BUY → HOLD"]


def test_new_rule_is_material_but_dropped_rule_is_not() -> None:
    changes = material_changes(state(Verdict.HOLD, ["R3"]), state(Verdict.HOLD, ["R1", "R3"]))
    assert changes == ["rule R1 baru aktif"]
    assert material_changes(state(Verdict.HOLD, ["R1", "R3"]), state(Verdict.HOLD, ["R3"])) == []


def test_confidence_drift_alone_is_not_material() -> None:
    before = state(Verdict.BUY, [])
    after = before.model_copy(update={"confidence_band": "MEDIUM"})
    assert material_changes(before, after) == []


# -- alert service ----------------------------------------------------------------


def build_service(
    container: Container, watchlist: InMemoryWatchlist, store: MemoryAlertState
) -> tuple[AlertService, CollectingSender]:
    sender = CollectingSender()
    service = AlertService(container.analysis, watchlist, store, sender, render_alert)
    return service, sender


async def test_first_run_seeds_state_silently(container: Container) -> None:
    watchlist = InMemoryWatchlist()
    watchlist.add("101", "BBCA")
    watchlist.add("102", "ANTM")
    store = MemoryAlertState()
    service, sender = build_service(container, watchlist, store)

    stats = await service.run(now=NOW)

    assert stats.tickers_checked == 2
    assert stats.alerts_sent == 0
    assert sender.sent == []
    assert store.states["BBCA"].verdict is Verdict.BUY
    assert "R1" in store.states["ANTM"].rule_ids


async def test_material_change_alerts_every_watcher(container: Container) -> None:
    watchlist = InMemoryWatchlist()
    watchlist.add("101", "BBCA")
    watchlist.add("202", "BBCA")
    store = MemoryAlertState()
    # Pretend yesterday's committee said SELL — today's BUY must alert.
    store.save(
        AlertState(
            ticker="BBCA",
            verdict=Verdict.SELL,
            rule_ids=[],
            confidence_band="LOW",
            updated_at=NOW - dt.timedelta(days=1),
        )
    )
    service, sender = build_service(container, watchlist, store)

    stats = await service.run(now=NOW)

    assert stats.alerts_sent == 2
    assert sorted(chat for chat, _ in sender.sent) == [101, 202]
    text = sender.sent[0][1]
    assert "SELL → BUY" in text
    assert "/analyze BBCA" in text
    assert store.states["BBCA"].verdict is Verdict.BUY  # state advanced


async def test_no_change_stays_silent_and_unknown_ticker_skipped(container: Container) -> None:
    watchlist = InMemoryWatchlist()
    watchlist.add("101", "BBCA")
    watchlist.add("101", "ZZZZ")  # not in the knowledge base
    store = MemoryAlertState()
    service, sender = build_service(container, watchlist, store)

    await service.run(now=NOW)  # seeds BBCA
    stats = await service.run(now=NOW)  # no change

    assert stats.alerts_sent == 0
    assert sender.sent == []
    assert "ZZZZ" not in store.states


def test_sqlite_alert_state_roundtrip(tmp_path: Path) -> None:
    db = Database(tmp_path / "alerts.db")
    store = SqliteAlertState(db)

    assert store.get("BBCA") is None
    store.save(state(Verdict.BUY, ["R3"]))
    loaded = store.get("BBCA")
    assert loaded is not None
    assert loaded.verdict is Verdict.BUY
    assert loaded.rule_ids == ["R3"]

    store.save(state(Verdict.HOLD, []))  # upsert
    reloaded = store.get("BBCA")
    assert reloaded is not None
    assert reloaded.verdict is Verdict.HOLD
    assert reloaded.rule_ids == []
    db.close()


# -- market event detection -------------------------------------------------------


def event_snapshot(series: list[PriceBar]) -> MarketSnapshot:
    return MarketSnapshot(
        profile=TickerProfile(ticker="TEST", name="Test Corp", sector="Perbankan"),
        bars=series,
        news=[],
        fundamentals=None,
        macro=MacroSnapshot(bi_rate_pct=6.0, usd_idr=15850),
        as_of=NOW,
        index_bars=[],
        sector_returns={},
    )


def test_sma_cross_up_detected() -> None:
    series = bars(59, daily_pct=-0.002)
    last = series[-1]
    spike = last.close * 1.15
    series.append(
        PriceBar(
            date=last.date + dt.timedelta(days=1),
            open=last.close,
            high=spike * 1.005,
            low=last.close * 0.995,
            close=spike,
            volume=1e6,
        )
    )
    ids = [event.event_id for event in market_events(event_snapshot(series))]
    assert "sma50_cross_up" in ids


def test_steady_decline_flags_oversold_only() -> None:
    ids = [event.event_id for event in market_events(event_snapshot(bars(30, daily_pct=-0.02)))]
    assert ids == ["rsi_oversold"]


def test_foreign_flow_spike_detected() -> None:
    series = [
        bar.model_copy(update={"net_foreign_bn_idr": 10.0 if i % 2 == 0 else -10.0})
        for i, bar in enumerate(bars(25))
    ]
    series[-1] = series[-1].model_copy(update={"net_foreign_bn_idr": 200.0})
    ids = [event.event_id for event in market_events(event_snapshot(series))]
    assert "flow_spike_masuk" in ids


def test_quiet_market_produces_no_events() -> None:
    assert market_events(event_snapshot(bars(60))) == []


def test_ongoing_event_alerts_once_until_it_clears() -> None:
    events = [
        MarketEvent("rsi_oversold", "RSI-14 25 — jenuh jual"),
        MarketEvent("sma50_cross_down", "harga jatuh ke bawah SMA-50 (95)"),
    ]
    previous = state(Verdict.HOLD, []).model_copy(update={"event_ids": ["rsi_oversold"]})
    current = state(Verdict.HOLD, []).model_copy(
        update={"event_ids": ["rsi_oversold", "sma50_cross_down"]}
    )
    assert material_changes(previous, current, events) == ["harga jatuh ke bawah SMA-50 (95)"]


def test_sqlite_roundtrips_event_ids(tmp_path: Path) -> None:
    db = Database(tmp_path / "alert-events.db")
    store = SqliteAlertState(db)
    store.save(state(Verdict.BUY, []).model_copy(update={"event_ids": ["rsi_overbought"]}))
    loaded = store.get("BBCA")
    assert loaded is not None
    assert loaded.event_ids == ["rsi_overbought"]
    db.close()
