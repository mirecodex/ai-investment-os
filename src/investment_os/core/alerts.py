from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from investment_os.core.agents.indicators import rsi, sma, zscore
from investment_os.core.service import AnalysisService, TickerNotFoundError
from investment_os.domain import Verdict
from investment_os.knowledge.ports import KnowledgeBase, MarketSnapshot
from investment_os.observability import get_logger, metrics
from investment_os.users.watchlist import WatchlistRepository

log = get_logger(__name__)


class AlertState(BaseModel):
    ticker: str
    verdict: Verdict
    rule_ids: list[str]
    confidence_band: str
    updated_at: dt.datetime
    event_ids: list[str] = Field(default_factory=list)


class AlertStateStore(Protocol):
    def get(self, ticker: str) -> AlertState | None: ...

    def save(self, state: AlertState) -> None: ...


class AlertSender(Protocol):
    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None: ...


class AlertRenderer(Protocol):
    def __call__(self, ticker: str, changes: list[str], summary: str) -> str: ...


class AlertHook(Protocol):
    async def __call__(self, ticker: str, changes: list[str], summary: str) -> None: ...


@dataclass(frozen=True)
class AlertRunStats:
    tickers_checked: int
    alerts_sent: int


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    description: str


def market_events(snapshot: MarketSnapshot) -> list[MarketEvent]:
    """Deterministic technical triggers on the latest bar.

    RSI/flow entries are conditions, not edges: once alerted they stay in the
    saved event set, so a watcher hears about them exactly once until the
    condition clears and re-enters. SMA crosses are single-bar edges already.
    """
    events: list[MarketEvent] = []
    closes = [bar.close for bar in snapshot.bars]

    sma_now = sma(closes, 50)
    sma_prev = sma(closes[:-1], 50)
    if sma_now is not None and sma_prev is not None and len(closes) >= 2:
        prev, last = closes[-2], closes[-1]
        if prev <= sma_prev and last > sma_now:
            events.append(
                MarketEvent("sma50_cross_up", f"harga menembus ke atas SMA-50 ({last:,.0f})")
            )
        elif prev >= sma_prev and last < sma_now:
            events.append(
                MarketEvent("sma50_cross_down", f"harga jatuh ke bawah SMA-50 ({last:,.0f})")
            )

    rsi_now = rsi(closes)
    if rsi_now is not None:
        if rsi_now >= 70:
            events.append(MarketEvent("rsi_overbought", f"RSI-14 {rsi_now:.0f} — jenuh beli"))
        elif rsi_now <= 30:
            events.append(MarketEvent("rsi_oversold", f"RSI-14 {rsi_now:.0f} — jenuh jual"))

    flows = [bar.net_foreign_bn_idr for bar in snapshot.bars]
    if len(flows) >= 21:
        z = zscore(flows[-21:-1], flows[-1])
        if z is not None and abs(z) >= 2.0:
            direction = "masuk" if flows[-1] > 0 else "keluar"
            events.append(
                MarketEvent(
                    f"flow_spike_{direction}",
                    f"arus asing {direction} tidak biasa ({flows[-1]:+,.0f} miliar, z={z:+.1f})",
                )
            )
    return events


def material_changes(
    previous: AlertState | None,
    current: AlertState,
    events: list[MarketEvent] | None = None,
) -> list[str]:
    """Human-readable change list; empty means stay silent."""
    if previous is None:
        return []  # first observation seeds state without alerting

    changes: list[str] = []
    if previous.verdict is not current.verdict:
        changes.append(f"keputusan berubah: {previous.verdict.value} → {current.verdict.value}")
    for rule_id in sorted(set(current.rule_ids) - set(previous.rule_ids)):
        changes.append(f"rule {rule_id} baru aktif")
    for event in events or []:
        if event.event_id not in previous.event_ids:
            changes.append(event.description)
    return changes


class AlertService:
    def __init__(
        self,
        analysis: AnalysisService,
        watchlist: WatchlistRepository,
        state_store: AlertStateStore,
        sender: AlertSender,
        render: AlertRenderer,
        *,
        kb: KnowledgeBase | None = None,
        hooks: list[AlertHook] | None = None,
    ) -> None:
        self._analysis = analysis
        self._watchlist = watchlist
        self._state = state_store
        self._sender = sender
        self._render = render
        self._kb = kb
        self._hooks = hooks or []

    async def run(self, *, now: dt.datetime | None = None) -> AlertRunStats:
        now = now or dt.datetime.now(tz=dt.UTC)

        watchers_by_ticker: dict[str, list[int]] = {}
        for user_id, ticker in self._watchlist.all_watchers():
            try:
                chat_id = int(user_id)
            except ValueError:
                continue  # non-chat principals (e.g. future web users) can't be pinged
            watchers_by_ticker.setdefault(ticker, []).append(chat_id)

        sent = 0
        for ticker, chat_ids in sorted(watchers_by_ticker.items()):
            try:
                result = await self._analysis.analyze(ticker)
            except TickerNotFoundError:
                log.warning("alert_ticker_missing", ticker=ticker)
                continue

            events: list[MarketEvent] = []
            if self._kb is not None:
                snapshot = self._kb.snapshot(ticker)
                if snapshot is not None:
                    events = market_events(snapshot)

            decision = result.report.decision
            current = AlertState(
                ticker=ticker,
                verdict=decision.verdict,
                rule_ids=sorted(t.rule_id for t in decision.triggered_rules),
                confidence_band=decision.confidence_band,
                updated_at=now,
                event_ids=sorted(event.event_id for event in events),
            )
            changes = material_changes(self._state.get(ticker), current, events)
            self._state.save(current)
            if not changes:
                continue

            summary = (
                f"{decision.verdict.value} · confidence "
                f"{decision.confidence * 100:.0f}% ({decision.confidence_band})"
            )
            # Side channels (webhooks) fire once per alert, not per watcher,
            # and never block chat delivery.
            for hook in self._hooks:
                try:
                    await hook(ticker, changes, summary)
                except Exception:
                    metrics.increment("alert_hook_failures")
                    log.exception("alert_hook_failed", ticker=ticker)

            text = self._render(ticker, changes, summary)
            for chat_id in chat_ids:
                try:
                    await self._sender.send_message(chat_id, text)
                    sent += 1
                except Exception:
                    metrics.increment("alert_delivery_failures")
                    log.exception("alert_delivery_failed", ticker=ticker, chat_id=chat_id)

        metrics.increment("alerts_sent", float(sent))
        log.info("alert_run_done", tickers=len(watchers_by_ticker), alerts=sent)
        return AlertRunStats(tickers_checked=len(watchers_by_ticker), alerts_sent=sent)
