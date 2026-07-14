"""Long-running bot process: update polling + scheduled jobs, one event loop.

Jobs:
- ``daily-brief`` — pre-market Market Brief to all subscribers (WIB, trading
  days only).
- ``kb-refresh`` — live mode only: rebuild the knowledge base from feeds and
  hot-swap it; a failed refresh keeps serving the previous snapshot.
"""

from __future__ import annotations

import asyncio
import datetime as dt

from investment_os.app.container import Container, build_container
from investment_os.config import Settings
from investment_os.interfaces.telegram.app import run_polling
from investment_os.interfaces.telegram.botapi import TelegramClient
from investment_os.interfaces.telegram.broadcast import broadcast_brief
from investment_os.knowledge.live import load_live_kb
from investment_os.knowledge.refreshable import RefreshableKnowledgeBase
from investment_os.observability import get_logger
from investment_os.pipelines.scheduler import DailyAt, Every, Job, Scheduler

log = get_logger(__name__)


async def run_bot(settings: Settings) -> None:
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("INVOS_TELEGRAM_BOT_TOKEN belum diset")

    refreshable: RefreshableKnowledgeBase | None = None
    if settings.data_mode == "live":
        inner = await load_live_kb(
            settings.universe_path, history_days=settings.market_history_days
        )
        refreshable = RefreshableKnowledgeBase(inner)

    container = build_container(settings, kb=refreshable)
    client = TelegramClient(token, poll_timeout_s=settings.telegram_poll_timeout_s)

    jobs = [_brief_job(settings, client, container)]
    if refreshable is not None:
        jobs.append(_refresh_job(settings, refreshable))
    scheduler = Scheduler(jobs)

    log.info("bot_started", data_mode=settings.data_mode, jobs=[j.name for j in jobs])
    await asyncio.gather(run_polling(client, container.router), scheduler.run())


def _brief_job(settings: Settings, client: TelegramClient, container: Container) -> Job:
    async def action() -> None:
        await broadcast_brief(client, container.subscriptions, container.analysis)

    return Job(
        name="daily-brief",
        schedule=DailyAt.parse(settings.brief_time_wib),
        action=action,
    )


def _refresh_job(settings: Settings, refreshable: RefreshableKnowledgeBase) -> Job:
    async def action() -> None:
        fresh = await load_live_kb(
            settings.universe_path, history_days=settings.market_history_days
        )
        if fresh.list_tickers():
            refreshable.swap(fresh)
            log.info("kb_refreshed", tickers=len(fresh.list_tickers()))
        else:
            log.warning("kb_refresh_empty", note="keeping previous snapshot")

    return Job(
        name="kb-refresh",
        schedule=Every(interval=dt.timedelta(minutes=settings.refresh_interval_minutes)),
        action=action,
    )
