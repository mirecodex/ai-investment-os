from __future__ import annotations

from pathlib import Path

from investment_os.app.container import Container
from investment_os.data import Database, SqliteSubscriptions
from investment_os.interfaces.telegram.broadcast import broadcast_brief


class CollectingSender:
    def __init__(self, *, fail_for: set[int] | None = None) -> None:
        self.sent: list[tuple[int, str]] = []
        self._fail_for = fail_for or set()

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
        if chat_id in self._fail_for:
            raise RuntimeError("chat blocked the bot")
        self.sent.append((chat_id, text))


def test_subscription_roundtrip(tmp_path: Path) -> None:
    db = Database(tmp_path / "subs.db")
    subs = SqliteSubscriptions(db)

    assert subs.subscribe("111", 111)
    assert not subs.subscribe("111", 111)
    assert subs.subscribe("222", 222)
    assert subs.chat_ids() == [111, 222]

    assert subs.unsubscribe("111")
    assert not subs.unsubscribe("111")
    assert subs.chat_ids() == [222]
    db.close()


async def test_broadcast_delivers_brief_and_isolates_failures(container: Container) -> None:
    container.subscriptions.subscribe("501", 501)
    container.subscriptions.subscribe("502", 502)
    container.subscriptions.subscribe("503", 503)

    sender = CollectingSender(fail_for={502})
    delivered = await broadcast_brief(sender, container.subscriptions, container.analysis)

    assert delivered == 2
    assert [chat for chat, _ in sender.sent] == [501, 503]
    assert all("Market Brief" in text for _, text in sender.sent)

    for user in ("501", "502", "503"):
        container.subscriptions.unsubscribe(user)


async def test_broadcast_without_subscribers_is_noop(container: Container) -> None:
    sender = CollectingSender()
    assert await broadcast_brief(sender, container.subscriptions, container.analysis) == 0
    assert sender.sent == []


async def test_router_subscribe_flow(container: Container) -> None:
    router = container.router
    assert "berlangganan" in (await router.handle("601", "/subscribe")).text
    assert "sudah berlangganan" in (await router.handle("601", "/subscribe")).text
    assert 601 in container.subscriptions.chat_ids()
    assert "dihentikan" in (await router.handle("601", "/unsubscribe")).text
    assert "belum berlangganan" in (await router.handle("601", "/unsubscribe")).text
