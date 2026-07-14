"""Transport-agnostic command handling.

The router maps parsed commands onto core services and returns reply text.
It knows nothing about the Bot API, so the exact same handling is exercised
by unit tests and by the polling client in ``app.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from investment_os.core.service import AnalysisService, TickerNotFoundError
from investment_os.interfaces.telegram import presenter
from investment_os.observability import get_logger
from investment_os.users import WatchlistRepository

log = get_logger(__name__)

_TICKER_RE = re.compile(r"^[A-Z]{4}$")


@dataclass(frozen=True)
class Reply:
    text: str
    parse_mode: str = "HTML"


class CommandRouter:
    def __init__(self, analysis: AnalysisService, watchlist: WatchlistRepository) -> None:
        self._analysis = analysis
        self._watchlist = watchlist

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
            case _:
                return Reply("Perintah tidak dikenal. Coba /help.")

    async def _analyze(self, argument: str) -> Reply:
        symbol = argument.upper()
        if not _TICKER_RE.match(symbol):
            return Reply("Format: /analyze <TICKER> — contoh: /analyze BBCA")
        try:
            result = await self._analysis.analyze(symbol)
        except TickerNotFoundError:
            return Reply(f"{symbol} belum tercakup. Coba /watchlist untuk emiten tersedia.")
        return Reply(presenter.render_report(result.report))

    def _show_watchlist(self, user_id: str) -> Reply:
        items = self._watchlist.list(user_id)
        if not items:
            return Reply("Watchlist kosong. Tambahkan dengan /add <TICKER>.")
        return Reply("Watchlist Anda:\n" + "\n".join(f"• {t}" for t in items))

    def _mutate_watchlist(self, user_id: str, argument: str, *, add: bool) -> Reply:
        symbol = argument.upper()
        if not _TICKER_RE.match(symbol):
            verb = "/add" if add else "/remove"
            return Reply(f"Format: {verb} <TICKER>")
        if add:
            changed = self._watchlist.add(user_id, symbol)
            return Reply(
                f"{symbol} ditambahkan ke watchlist." if changed else f"{symbol} sudah ada."
            )
        changed = self._watchlist.remove(user_id, symbol)
        return Reply(
            f"{symbol} dihapus dari watchlist." if changed else f"{symbol} tidak ada di watchlist."
        )
