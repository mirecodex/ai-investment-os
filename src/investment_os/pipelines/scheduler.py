"""Async job scheduler with WIB-aware daily triggers.

Purpose-built rather than a cron dependency: two schedule shapes (daily at a
wall-clock time in WIB, fixed interval), error isolation per job, and
injectable clock/sleep so tests run in virtual time. Event-driven triggers
(docs/fase-3, doc 06) plug in later as a third schedule shape.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

WIB = dt.timezone(dt.timedelta(hours=7), name="WIB")


class Schedule(Protocol):
    def next_after(self, moment: dt.datetime) -> dt.datetime: ...


@dataclass(frozen=True)
class DailyAt:
    """Fires at a fixed WIB wall-clock time; optionally trading days only."""

    hour: int
    minute: int = 0
    weekdays_only: bool = True

    def next_after(self, moment: dt.datetime) -> dt.datetime:
        local = moment.astimezone(WIB)
        candidate = local.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if candidate <= local:
            candidate += dt.timedelta(days=1)
        while self.weekdays_only and candidate.weekday() >= 5:
            candidate += dt.timedelta(days=1)
        return candidate.astimezone(dt.UTC)

    @classmethod
    def parse(cls, hhmm: str, *, weekdays_only: bool = True) -> DailyAt:
        hour, _, minute = hhmm.partition(":")
        return cls(hour=int(hour), minute=int(minute or 0), weekdays_only=weekdays_only)


@dataclass(frozen=True)
class Every:
    interval: dt.timedelta

    def next_after(self, moment: dt.datetime) -> dt.datetime:
        return moment + self.interval


@dataclass(frozen=True)
class Job:
    name: str
    schedule: Schedule
    action: Callable[[], Awaitable[None]]


class Scheduler:
    def __init__(
        self,
        jobs: list[Job],
        *,
        now: Callable[[], dt.datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if not jobs:
            raise ValueError("scheduler needs at least one job")
        self._jobs = {job.name: job for job in jobs}
        self._now = now or (lambda: dt.datetime.now(tz=dt.UTC))
        if sleep is None:
            import asyncio

            sleep = asyncio.sleep
        self._sleep = sleep

    async def run(self, *, iterations: int | None = None) -> None:
        """Run forever (or for N job firings, for tests and drain scenarios)."""
        due = {name: job.schedule.next_after(self._now()) for name, job in self._jobs.items()}
        for name, at in due.items():
            log.info("job_scheduled", job=name, next_run=at.isoformat())

        fired = 0
        while iterations is None or fired < iterations:
            name = min(due, key=lambda n: due[n])
            wait_s = (due[name] - self._now()).total_seconds()
            if wait_s > 0:
                await self._sleep(wait_s)

            await self._execute(self._jobs[name])
            fired += 1
            # Schedule strictly after the planned firing time so a slow job
            # cannot make DailyAt re-fire the same slot.
            due[name] = self._jobs[name].schedule.next_after(max(self._now(), due[name]))

    async def _execute(self, job: Job) -> None:
        log.info("job_started", job=job.name)
        try:
            await job.action()
        except Exception:
            metrics.increment("scheduler_job_failures", job=job.name)
            log.exception("job_failed", job=job.name)
        else:
            metrics.increment("scheduler_job_runs", job=job.name)
