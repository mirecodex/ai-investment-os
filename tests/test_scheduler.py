from __future__ import annotations

import datetime as dt

from investment_os.pipelines.scheduler import WIB, DailyAt, Every, Job, Scheduler


def wib(year: int, month: int, day: int, hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=WIB)


class VirtualClock:
    def __init__(self, start: dt.datetime) -> None:
        self.current = start

    def now(self) -> dt.datetime:
        return self.current

    async def sleep(self, seconds: float) -> None:
        self.current += dt.timedelta(seconds=seconds)


def test_daily_at_same_day_when_before_slot() -> None:
    # Monday 2026-07-13, 06:00 WIB → fires 07:30 the same morning
    at = DailyAt.parse("07:30").next_after(wib(2026, 7, 13, 6, 0))
    assert at == wib(2026, 7, 13, 7, 30)


def test_daily_at_rolls_to_next_day_after_slot() -> None:
    at = DailyAt.parse("07:30").next_after(wib(2026, 7, 13, 8, 0))
    assert at == wib(2026, 7, 14, 7, 30)


def test_daily_at_skips_weekend() -> None:
    # Friday 2026-07-17 after the slot → Monday 2026-07-20
    at = DailyAt.parse("07:30").next_after(wib(2026, 7, 17, 9, 0))
    assert at == wib(2026, 7, 20, 7, 30)
    assert at.astimezone(WIB).weekday() == 0


def test_daily_at_weekends_allowed_when_configured() -> None:
    at = DailyAt(hour=7, minute=30, weekdays_only=False).next_after(wib(2026, 7, 17, 9, 0))
    assert at == wib(2026, 7, 18, 7, 30)


async def test_scheduler_fires_jobs_in_due_order() -> None:
    clock = VirtualClock(wib(2026, 7, 13, 6, 0))
    fired: list[str] = []

    async def make(name: str) -> None:
        fired.append(name)

    jobs = [
        Job("hourly", Every(dt.timedelta(hours=1)), lambda: make("hourly")),
        Job("brief", DailyAt.parse("07:30"), lambda: make("brief")),
    ]
    await Scheduler(jobs, now=clock.now, sleep=clock.sleep).run(iterations=3)

    assert fired == ["hourly", "brief", "hourly"]


async def test_failing_job_does_not_stop_the_loop() -> None:
    clock = VirtualClock(wib(2026, 7, 13, 6, 0))
    runs: list[str] = []

    async def bad() -> None:
        runs.append("bad")
        raise RuntimeError("boom")

    async def good() -> None:
        runs.append("good")

    jobs = [
        Job("bad", Every(dt.timedelta(minutes=10)), bad),
        Job("good", Every(dt.timedelta(minutes=15)), good),
    ]
    await Scheduler(jobs, now=clock.now, sleep=clock.sleep).run(iterations=4)

    assert runs.count("bad") >= 2
    assert "good" in runs


async def test_slow_job_does_not_refire_same_daily_slot() -> None:
    clock = VirtualClock(wib(2026, 7, 13, 7, 29))
    fired: list[dt.datetime] = []

    async def slow() -> None:
        fired.append(clock.current)
        await clock.sleep(3600)  # job takes an hour

    await Scheduler(
        [Job("brief", DailyAt.parse("07:30"), slow)], now=clock.now, sleep=clock.sleep
    ).run(iterations=2)

    assert fired[0].astimezone(WIB).date() == dt.date(2026, 7, 13)
    assert fired[1].astimezone(WIB).date() == dt.date(2026, 7, 14)
