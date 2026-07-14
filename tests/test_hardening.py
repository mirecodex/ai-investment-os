from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest

from investment_os.app.container import Container, build_container
from investment_os.app.runtime import _supervise
from investment_os.config import Settings
from investment_os.interfaces.telegram.app import run_polling
from investment_os.interfaces.telegram.botapi import TelegramApiError, TelegramClient
from investment_os.interfaces.telegram.broadcast import broadcast_brief
from investment_os.pipelines.scheduler import DailyAt, Job, Scheduler
from tests.conftest import FIXTURE_PATH


def make_client(handler, *, max_attempts: int = 3) -> TelegramClient:  # type: ignore[no-untyped-def]
    return TelegramClient(
        "TEST:TOKEN", max_attempts=max_attempts, transport=httpx.MockTransport(handler)
    )


def patch_sleep(monkeypatch: pytest.MonkeyPatch, waits: list[float]) -> None:
    async def instant(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("investment_os.interfaces.telegram.botapi.asyncio.sleep", instant)


async def test_client_honors_retry_after_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    patch_sleep(monkeypatch, waits)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                json={"ok": False, "parameters": {"retry_after": 7}},
            )
        return httpx.Response(200, json={"ok": True, "result": []})

    client = make_client(handler)
    await client.send_message(42, "halo")
    await client.close()

    assert calls == 2
    assert waits == [7.0]  # Telegram's retry_after wins over the local backoff


async def test_client_does_not_retry_permanent_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            403, json={"ok": False, "description": "Forbidden: bot was blocked by the user"}
        )

    client = make_client(handler)
    with pytest.raises(TelegramApiError) as excinfo:
        await client.send_message(42, "halo")
    await client.close()

    assert calls == 1
    assert excinfo.value.is_blocked
    assert not excinfo.value.is_auth_failure


async def test_client_survives_non_json_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    patch_sleep(monkeypatch, waits)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(502, text="<html>Bad Gateway</html>")
        return httpx.Response(200, json={"ok": True, "result": []})

    client = make_client(handler)
    await client.send_message(42, "halo")
    await client.close()

    assert calls == 3
    assert waits == [1.0, 2.0]


class ScriptedTransport:
    def __init__(self, batches: list[Any]) -> None:
        self.batches = batches
        self.offsets: list[int | None] = []
        self.sent: list[tuple[int, str]] = []

    async def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        self.offsets.append(offset)
        if not self.batches:
            raise RuntimeError("script exhausted")
        item = self.batches.pop(0)
        if isinstance(item, Exception):
            raise item
        return list(item)

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
        self.sent.append((chat_id, text))


async def test_polling_survives_transient_outage(container: Container) -> None:
    update = {"update_id": 7, "message": {"text": "/help", "chat": {"id": 42}}}
    transport = ScriptedTransport([httpx.ConnectError("network down"), [update]])

    with pytest.raises(RuntimeError, match="script exhausted"):
        await run_polling(transport, container.router, retry_base_s=0)

    assert [chat for chat, _ in transport.sent] == [42]
    assert transport.offsets == [None, None, 8]  # retried, then acked past update 7


async def test_polling_dies_fast_on_bad_token(container: Container) -> None:
    transport = ScriptedTransport([TelegramApiError("getUpdates", 401, "Unauthorized")])

    with pytest.raises(TelegramApiError) as excinfo:
        await run_polling(transport, container.router, retry_base_s=0)
    assert excinfo.value.is_auth_failure


class RejectingSender:
    def __init__(self, blocked: set[int]) -> None:
        self.blocked = blocked
        self.sent: list[int] = []

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
        if chat_id in self.blocked:
            raise TelegramApiError("sendMessage", 403, "Forbidden: bot was blocked by the user")
        self.sent.append(chat_id)


async def test_broadcast_paces_and_drops_blocked_chats(container: Container) -> None:
    for user, chat in (("701", 701), ("702", 702), ("703", 703)):
        container.subscriptions.subscribe(user, chat)
    sender = RejectingSender(blocked={702})
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)

    delivered = await broadcast_brief(
        sender, container.subscriptions, container.analysis, pace_s=0.04, sleep=sleep
    )

    assert delivered == 2
    assert sender.sent == [701, 703]
    assert waits == [0.04, 0.04]  # pacing between sends, not before the first
    assert 702 not in container.subscriptions.chat_ids()  # blocked chat dropped

    for user in ("701", "703"):
        container.subscriptions.unsubscribe(user)


async def test_supervisor_cleans_up_when_polling_crashes(tmp_path: Path) -> None:
    settings = Settings(
        fixtures_path=FIXTURE_PATH,
        database_path=tmp_path / "supervise.db",
        telegram_bot_token=None,
        llm_provider="off",
    )
    fresh = build_container(settings)

    class CrashingClient:
        def __init__(self) -> None:
            self.closed = False

        async def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
            raise TelegramApiError("getUpdates", 401, "Unauthorized")

        async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
            raise AssertionError("unexpected send")

        async def close(self) -> None:
            self.closed = True

    async def never_fires() -> None:
        raise AssertionError("job must not run")

    scheduler = Scheduler([Job(name="idle", schedule=DailyAt(hour=3), action=never_fires)])
    client = CrashingClient()

    with pytest.raises(TelegramApiError):
        await _supervise(client, fresh, scheduler)  # type: ignore[arg-type]

    assert client.closed
    with pytest.raises(sqlite3.ProgrammingError), fresh.db.transaction() as conn:
        conn.execute("SELECT 1")
