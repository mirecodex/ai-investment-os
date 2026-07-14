from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import signal

from investment_os.app.container import Container, build_container
from investment_os.config import Settings
from investment_os.core.alerts import AlertService
from investment_os.interfaces.telegram import presenter
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

    jobs = [_brief_job(settings, client, container), _alert_job(settings, client, container)]
    if refreshable is not None:
        jobs.append(_refresh_job(settings, refreshable))
    scheduler = Scheduler(jobs)

    log.info("bot_started", data_mode=settings.data_mode, jobs=[j.name for j in jobs])
    await _supervise(client, container, scheduler)


async def _supervise(client: TelegramClient, container: Container, scheduler: Scheduler) -> None:
    # One task dying (or SIGTERM from Docker) must bring the whole process
    # down cleanly: cancel the rest, flush the HTTP client, close SQLite.
    # A crash propagates after cleanup so the supervisor restarts us.
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signum, stop.set)

    tasks = [
        asyncio.create_task(run_polling(client, container.router), name="telegram-polling"),
        asyncio.create_task(scheduler.run(), name="scheduler"),
    ]
    waiter = asyncio.create_task(stop.wait(), name="signal-waiter")
    try:
        done, _ = await asyncio.wait([*tasks, waiter], return_when=asyncio.FIRST_COMPLETED)
        if waiter in done:
            log.info("bot_stopping", reason="signal")
            return
        finished = done.pop()
        error = finished.exception()
        if error is not None:
            log.error("bot_task_crashed", task=finished.get_name(), error=repr(error))
            raise error
        log.warning("bot_task_exited", task=finished.get_name())
    finally:
        waiter.cancel()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, waiter, return_exceptions=True)
        await client.close()
        container.db.close()
        log.info("bot_stopped")


def _brief_job(settings: Settings, client: TelegramClient, container: Container) -> Job:
    async def action() -> None:
        await broadcast_brief(client, container.subscriptions, container.analysis)

    return Job(
        name="daily-brief",
        schedule=DailyAt.parse(settings.brief_time_wib),
        action=action,
    )


def _alert_job(settings: Settings, client: TelegramClient, container: Container) -> Job:
    service = AlertService(
        container.analysis,
        container.watchlist,
        container.alert_state,
        client,
        presenter.render_alert,
    )

    async def action() -> None:
        await service.run()

    return Job(
        name="watchlist-alerts",
        schedule=DailyAt.parse(settings.alert_time_wib),
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
