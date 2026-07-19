from __future__ import annotations

import argparse
import asyncio
import html
import re
import sys
from pathlib import Path

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
    sub.add_parser("health", help="wiring/database healthcheck (used by Docker)")

    serve_api = sub.add_parser("serve-api", help="start the internal REST API")
    serve_api.add_argument("--host", default="127.0.0.1")
    serve_api.add_argument("--port", type=int, default=8000)

    history = sub.add_parser("history", help="show stored recommendations")
    history.add_argument("--ticker", default=None)
    history.add_argument("--limit", type=int, default=10)

    evaluate = sub.add_parser("eval", help="run the golden regression suite")
    evaluate.add_argument("--suite", default=None, help="path to a golden suite JSON")

    calibration = sub.add_parser("calibration", help="direction accuracy & calibration report")
    calibration.add_argument("--horizon", default="20d")

    record_outcomes = sub.add_parser(
        "record-outcomes", help="record realized returns for matured recommendations"
    )
    record_outcomes.add_argument("--horizon-days", type=int, default=None)

    backtest = sub.add_parser("backtest", help="point-in-time replay over the knowledge base")
    backtest.add_argument("--horizon-days", type=int, default=20)
    backtest.add_argument("--stride", type=int, default=5)
    backtest.add_argument("--min-history", type=int, default=60)

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

        try:
            asyncio.run(run_bot(settings))
        except KeyboardInterrupt:
            # Windows: no loop signal handlers, Ctrl+C surfaces here instead.
            print("Bot dihentikan.")
        return 0

    if args.command == "health":
        # Cheap and side-effect-free: verify wiring, KB fixture, and a DB
        # round-trip. Always fixture mode so the probe never hits the network.
        try:
            probe = build_container(settings.model_copy(update={"data_mode": "fixture"}))
            if not probe.kb.list_tickers():
                raise RuntimeError("knowledge base kosong")
            with probe.db.transaction() as conn:
                conn.execute("SELECT 1")
        except Exception as exc:
            print(f"unhealthy: {exc}", file=sys.stderr)
            return 1
        print("ok")
        return 0

    if args.command == "serve-api":
        import uvicorn

        from investment_os.interfaces.api import create_app

        api_container = build_container(settings)
        uvicorn.run(create_app(api_container), host=args.host, port=args.port)
        return 0

    if args.command == "backtest":
        from investment_os.eval import run_backtest
        from investment_os.knowledge.fixtures import load_fixture_kb

        if settings.data_mode == "live":
            from investment_os.knowledge.live import load_live_kb

            bt_kb = asyncio.run(
                load_live_kb(settings.universe_path, history_days=settings.market_history_days)
            )
        else:
            bt_kb = load_fixture_kb(settings.fixtures_path)

        bt = asyncio.run(
            run_backtest(
                bt_kb,
                horizon_days=args.horizon_days,
                stride_days=args.stride,
                min_history=args.min_history,
            )
        )
        rel = bt.reliability
        print(
            f"Backtest horizon {bt.horizon_days} hari bursa: {bt.sample_count} keputusan "
            f"di-replay, {rel.directional_count} terarah (BUY/SELL)."
        )
        if rel.overall_hit_rate is None:
            print("Tidak ada keputusan terarah — komite menahan diri sepanjang periode.")
        else:
            assert rel.ece is not None
            print(f"Hit rate arah {rel.overall_hit_rate:.0%} · ECE {rel.ece:.3f}")
            for bucket in rel.buckets:
                print(
                    f"  conf {bucket.low:.1f}-{bucket.high:.1f}: n={bucket.count}, "
                    f"rata2 conf {bucket.avg_confidence:.2f}, hit {bucket.hit_rate:.0%}"
                )
        print("Catatan: backtest untuk kalibrasi, bukan jaminan performa masa depan.")
        return 0

    if args.command == "eval":
        from investment_os.eval import GoldenSuite, run_suite

        suite_path = Path(args.suite) if args.suite else settings.golden_path
        suite = GoldenSuite.load(suite_path)
        results = asyncio.run(run_suite(suite, repo_root=settings.repo_root))

        failed = [r for r in results if not r.passed]
        for case_result in results:
            status = "PASS" if case_result.passed else "FAIL"
            print(f"[{status}] {case_result.case.name}: {case_result.summary}")
            for failure in case_result.failures:
                print(f"       - {failure}")
        print(f"\n{len(results) - len(failed)}/{len(results)} kasus lulus")
        return 1 if failed else 0

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
    elif args.command == "record-outcomes":
        from investment_os.core.outcomes import OutcomeTracker

        horizon_days = args.horizon_days or settings.outcome_horizon_days
        tracker = OutcomeTracker(container.kb, container.recommendations, horizon_days=horizon_days)
        recorded = tracker.run()
        print(
            f"{recorded} outcome tercatat untuk horizon {horizon_days} hari bursa. "
            f"Lihat: investment-os calibration --horizon {horizon_days}d"
        )
    elif args.command == "calibration":
        from investment_os.eval import reliability_report

        outcomes = container.recommendations.calibration_pairs(horizon=args.horizon)
        report = reliability_report(outcomes, horizon=args.horizon)
        if report.directional_count == 0:
            print(
                f"Belum ada outcome terarah (BUY/SELL) untuk horizon {args.horizon}. "
                "Rekam dengan record_outcome seiring waktu berjalan."
            )
        else:
            print(
                f"Horizon {report.horizon}: {report.directional_count} outcome terarah, "
                f"hit rate {report.overall_hit_rate:.0%}, ECE {report.ece:.3f}"
            )
            for bucket in report.buckets:
                print(
                    f"  conf {bucket.low:.1f}-{bucket.high:.1f}: n={bucket.count}, "
                    f"rata2 conf {bucket.avg_confidence:.2f}, hit {bucket.hit_rate:.0%}"
                )
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
