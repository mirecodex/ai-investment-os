from __future__ import annotations

import re
from dataclasses import dataclass

from investment_os.core.service import AnalysisService, TickerNotFoundError
from investment_os.interfaces.telegram import presenter
from investment_os.observability import get_logger
from investment_os.users import WatchlistRepository
from investment_os.users.subscriptions import SubscriptionRepository

log = get_logger(__name__)

_TICKER_RE = re.compile(r"^[A-Z]{4}$")


@dataclass(frozen=True)
class Reply:
    text: str
    parse_mode: str = "HTML"


class CommandRouter:
    def __init__(
        self,
        analysis: AnalysisService,
        watchlist: WatchlistRepository,
        subscriptions: SubscriptionRepository | None = None,
    ) -> None:
        self._analysis = analysis
        self._watchlist = watchlist
        self._subscriptions = subscriptions

    async def handle(self, user_id: str, text: str) -> Reply:
        command, _, argument = text.strip().partition(" ")
        command = command.split("@", 1)[0].lower()
        argument = argument.strip()

        match command:
            case "/start":
                return Reply(presenter.render_start())
            case "/help":
                return Reply(presenter.render_help())
            case "/brief":
                return Reply(presenter.render_brief(self._analysis.daily_brief()))
            case "/analyze":
                return await self._analyze(argument)
            case "/watchlist":
                return self._show_watchlist(user_id)
            case "/add":
                return self._mutate_watchlist(user_id, argument, add=True)
            case "/remove":
                return self._mutate_watchlist(user_id, argument, add=False)
            case "/subscribe":
                return self._subscribe(user_id)
            case "/unsubscribe":
                return self._unsubscribe(user_id)
            case _:
                return Reply("Perintah tidak dikenal. Coba /help.")

    async def _analyze(self, argument: str) -> Reply:
        symbol = argument.upper()
        if not _TICKER_RE.match(symbol):
            return Reply("Format: /analyze &lt;TICKER&gt; — contoh: /analyze BBCA")
        try:
            result = await self._analysis.analyze(symbol)
        except TickerNotFoundError:
            return Reply(f"{symbol} belum tercakup. Coba /watchlist untuk emiten tersedia.")
        return Reply(presenter.render_report(result.report))

    def _show_watchlist(self, user_id: str) -> Reply:
        items = self._watchlist.list(user_id)
        if not items:
            return Reply("Watchlist kosong. Tambahkan dengan /add &lt;TICKER&gt;.")
        return Reply("Watchlist Anda:\n" + "\n".join(f"• {t}" for t in items))

    def _subscribe(self, user_id: str) -> Reply:
        if self._subscriptions is None:
            return Reply("Langganan brief belum aktif di deployment ini.")
        try:
            chat_id = int(user_id)
        except ValueError:
            return Reply("Langganan hanya tersedia lewat chat Telegram.")
        if self._subscriptions.subscribe(user_id, chat_id):
            return Reply("Anda berlangganan Market Brief harian (pra-market WIB).")
        return Reply("Anda sudah berlangganan Market Brief harian.")

    def _unsubscribe(self, user_id: str) -> Reply:
        if self._subscriptions is None:
            return Reply("Langganan brief belum aktif di deployment ini.")
        if self._subscriptions.unsubscribe(user_id):
            return Reply("Langganan Market Brief dihentikan.")
        return Reply("Anda belum berlangganan Market Brief.")

    def _mutate_watchlist(self, user_id: str, argument: str, *, add: bool) -> Reply:
        symbol = argument.upper()
        if not _TICKER_RE.match(symbol):
            verb = "/add" if add else "/remove"
            return Reply(f"Format: {verb} &lt;TICKER&gt;")
        if add:
            changed = self._watchlist.add(user_id, symbol)
            return Reply(
                f"{symbol} ditambahkan ke watchlist." if changed else f"{symbol} sudah ada."
            )
        changed = self._watchlist.remove(user_id, symbol)
        return Reply(
            f"{symbol} dihapus dari watchlist." if changed else f"{symbol} tidak ada di watchlist."
        )
