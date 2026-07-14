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
from investment_os.observability import configure_logging, metrics

_TAG_RE = re.compile(r"<[^>]+>")


def _plain(rendered_html: str) -> str:
    return html.unescape(_TAG_RE.sub("", rendered_html))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="investment-os")
    parser.add_argument("--show-metrics", action="store_true", help="dump metrics after the run")
    parser.add_argument(
        "--live",
        action="store_true",
        help="pull live market data + RSS news instead of the offline fixture",
    )
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
    if args.live:
        settings = settings.model_copy(update={"data_mode": "live"})
    configure_logging(json_output=settings.log_json)

    if args.command == "serve-telegram":
        if not settings.telegram_bot_token:
            print("error: INVOS_TELEGRAM_BOT_TOKEN belum diset", file=sys.stderr)
            return 2
        from investment_os.app.runtime import run_bot

        asyncio.run(run_bot(settings))
        return 0

    kb = None
    if settings.data_mode == "live":
        from investment_os.knowledge.live import load_live_kb

        kb = asyncio.run(
            load_live_kb(settings.universe_path, history_days=settings.market_history_days)
        )
        if not kb.list_tickers():
            print(
                "peringatan: tidak ada data live yang berhasil diambil — "
                "periksa koneksi/akses jaringan. Jalankan tanpa --live untuk mode fixture.",
                file=sys.stderr,
            )
    container = build_container(settings, kb=kb)

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
    if args.show_metrics:
        for name, value in sorted(metrics.snapshot().items()):
            print(f"{name} = {value:.2f}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
