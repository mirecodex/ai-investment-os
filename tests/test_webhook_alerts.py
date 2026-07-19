from __future__ import annotations

import json

import httpx
import pytest

from investment_os.app.container import Container
from investment_os.core.alerts import AlertService, AlertState
from investment_os.domain import Verdict
from investment_os.interfaces.telegram.presenter import render_alert
from investment_os.interfaces.webhook import WebhookNotifier
from investment_os.users import InMemoryWatchlist
from tests.conftest import NOW
from tests.test_alerts import CollectingSender, MemoryAlertState


def make_notifier(handler, fmt: str = "generic") -> WebhookNotifier:  # type: ignore[no-untyped-def]
    return WebhookNotifier(
        "https://hooks.example/x", fmt=fmt, transport=httpx.MockTransport(handler)
    )


async def deliver_once(fmt: str) -> dict[str, object]:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200)

    notifier = make_notifier(handler, fmt)
    await notifier.notify("BBCA", ["keputusan berubah: HOLD → BUY"], "BUY · 75% (HIGH)")
    await notifier.close()
    return bodies[0]


async def test_payload_shape_per_format() -> None:
    for fmt, expected_key in (("generic", "event"), ("discord", "content"), ("slack", "text")):
        body = await deliver_once(fmt)
        assert expected_key in body
        flat = json.dumps(body)
        assert "BBCA" in flat and "HOLD" in flat  # content carried in every shape

    with pytest.raises(ValueError):
        WebhookNotifier("https://hooks.example/x", fmt="telegram")


async def test_notifier_retries_transient_then_delivers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []

    async def instant(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("investment_os.interfaces.webhook.asyncio.sleep", instant)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls == 1 else httpx.Response(204)

    notifier = make_notifier(handler)
    await notifier.notify("ANTM", ["rule R1 baru aktif"], "HOLD · 60% (MEDIUM)")
    await notifier.close()
    assert calls == 2 and waits == [1.0]


async def test_alert_service_fires_hook_once_and_survives_hook_failure(
    container: Container,
) -> None:
    watchlist = InMemoryWatchlist()
    watchlist.add("801", "BBCA")
    watchlist.add("802", "BBCA")  # two watchers, hook must still fire once
    store = MemoryAlertState()
    store.save(
        AlertState(
            ticker="BBCA",
            verdict=Verdict.SELL,
            rule_ids=[],
            confidence_band="LOW",
            updated_at=NOW,
        )
    )

    hook_calls: list[tuple[str, list[str], str]] = []

    async def recording_hook(ticker: str, changes: list[str], summary: str) -> None:
        hook_calls.append((ticker, changes, summary))

    async def broken_hook(ticker: str, changes: list[str], summary: str) -> None:
        raise RuntimeError("webhook down")

    sender = CollectingSender()
    service = AlertService(
        container.analysis,
        watchlist,
        store,
        sender,
        render_alert,
        hooks=[broken_hook, recording_hook],
    )
    stats = await service.run(now=NOW)

    assert stats.alerts_sent == 2  # chat delivery unaffected by the broken hook
    assert len(hook_calls) == 1
    ticker, changes, summary = hook_calls[0]
    assert ticker == "BBCA"
    assert any("SELL" in c and "BUY" in c for c in changes)
    assert "confidence" in summary
