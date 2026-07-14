"""CLI entry points.

``investment-os analyze BBCA`` and ``investment-os brief`` run the full
committee offline against the fixture knowledge base — the fastest way to see
the engine work end to end. ``investment-os serve-telegram`` starts the bot
(requires INVOS_TELEGRAM_BOT_TOKEN).
"""

from __future__ import annotations

import argparse
import asyncio
import html
import re
import sys

from investment_os.app.container import build_container
from investment_os.config import load_settings
from investment_os.core.service import TickerNotFoundError
from investment_os.interfaces.telegram import presenter
from investment_os.interfaces.telegram.app import run_polling
from investment_os.interfaces.telegram.botapi import TelegramClient
from investment_os.observability import configure_logging, metrics

_TAG_RE = re.compile(r"<[^>]+>")


def _plain(rendered_html: str) -> str:
    return html.unescape(_TAG_RE.sub("", rendered_html))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="investment-os")
    parser.add_argument("--show-metrics", action="store_true", help="dump metrics after the run")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="run the investment committee for one ticker")
    analyze.add_argument("ticker")

    sub.add_parser("brief", help="print today's market brief")
    sub.add_parser("tickers", help="list tickers in the knowledge base")
    sub.add_parser("serve-telegram", help="start the Telegram bot (long polling)")

    history = sub.add_parser("history", help="show stored recommendations")
    history.add_argument("--ticker", default=None)
    history.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    settings = load_settings()
    configure_logging(json_output=settings.log_json)
    container = build_container(settings)

    exit_code = 0
    if args.command == "analyze":
        try:
            result = asyncio.run(container.analysis.analyze(args.ticker))
            print(_plain(presenter.render_report(result.report)))
        except TickerNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            exit_code = 1
    elif args.command == "brief":
        print(_plain(presenter.render_brief(container.analysis.daily_brief())))
    elif args.command == "tickers":
        for profile in container.kb.list_tickers():
            print(f"{profile.ticker}  {profile.name} ({profile.sector})")
    elif args.command == "history":
        records = container.recommendations.history(args.ticker, limit=args.limit)
        if not records:
            print("Belum ada rekomendasi tersimpan.")
        for record in records:
            rules = (
                f" rules={','.join(record.triggered_rule_ids)}" if record.triggered_rule_ids else ""
            )
            print(
                f"#{record.id} {record.created_at:%Y-%m-%d %H:%M} {record.ticker} "
                f"{record.verdict.value} ({record.confidence * 100:.0f}% "
                f"{record.confidence_band}){rules} [{record.engine_version}]"
            )
    elif args.command == "serve-telegram":
        token = settings.telegram_bot_token
        if not token:
            print("error: INVOS_TELEGRAM_BOT_TOKEN belum diset", file=sys.stderr)
            return 2
        client = TelegramClient(token, poll_timeout_s=settings.telegram_poll_timeout_s)
        asyncio.run(run_polling(client, container.router))

    if args.show_metrics:
        for name, value in sorted(metrics.snapshot().items()):
            print(f"{name} = {value:.2f}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
