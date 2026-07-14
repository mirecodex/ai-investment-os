from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from investment_os.core.service import AnalysisService, TickerNotFoundError
from investment_os.domain import Verdict
from investment_os.observability import get_logger, metrics
from investment_os.users.watchlist import WatchlistRepository

log = get_logger(__name__)


class AlertState(BaseModel):
    ticker: str
    verdict: Verdict
    rule_ids: list[str]
    confidence_band: str
    updated_at: dt.datetime


class AlertStateStore(Protocol):
    def get(self, ticker: str) -> AlertState | None: ...

    def save(self, state: AlertState) -> None: ...


class AlertSender(Protocol):
    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None: ...


class AlertRenderer(Protocol):
    def __call__(self, ticker: str, changes: list[str], summary: str) -> str: ...


@dataclass(frozen=True)
class AlertRunStats:
    tickers_checked: int
    alerts_sent: int


def material_changes(previous: AlertState | None, current: AlertState) -> list[str]:
    """Human-readable change list; empty means stay silent."""
    if previous is None:
        return []  # first observation seeds state without alerting

    changes: list[str] = []
    if previous.verdict is not current.verdict:
        changes.append(f"keputusan berubah: {previous.verdict.value} → {current.verdict.value}")
    for rule_id in sorted(set(current.rule_ids) - set(previous.rule_ids)):
        changes.append(f"rule {rule_id} baru aktif")
    return changes


class AlertService:
    def __init__(
        self,
        analysis: AnalysisService,
        watchlist: WatchlistRepository,
        state_store: AlertStateStore,
        sender: AlertSender,
        render: AlertRenderer,
    ) -> None:
        self._analysis = analysis
        self._watchlist = watchlist
        self._state = state_store
        self._sender = sender
        self._render = render

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

            decision = result.report.decision
            current = AlertState(
                ticker=ticker,
                verdict=decision.verdict,
                rule_ids=sorted(t.rule_id for t in decision.triggered_rules),
                confidence_band=decision.confidence_band,
                updated_at=now,
            )
            changes = material_changes(self._state.get(ticker), current)
            self._state.save(current)
            if not changes:
                continue

            summary = (
                f"{decision.verdict.value} · confidence "
                f"{decision.confidence * 100:.0f}% ({decision.confidence_band})"
            )
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
