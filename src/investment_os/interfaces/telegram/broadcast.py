"""Push delivery: daily Market Brief to subscribed chats."""

from __future__ import annotations

from typing import Protocol

from investment_os.core.service import AnalysisService
from investment_os.interfaces.telegram import presenter
from investment_os.observability import get_logger, metrics
from investment_os.users.subscriptions import SubscriptionRepository

log = get_logger(__name__)


class MessageSender(Protocol):
    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None: ...


async def broadcast_brief(
    sender: MessageSender,
    subscriptions: SubscriptionRepository,
    analysis: AnalysisService,
) -> int:
    """Render today's brief once, deliver to every subscriber. Returns sends."""
    chat_ids = subscriptions.chat_ids()
    if not chat_ids:
        log.info("brief_broadcast_skipped", reason="no_subscribers")
        return 0

    text = presenter.render_brief(analysis.daily_brief())
    delivered = 0
    for chat_id in chat_ids:
        try:
            await sender.send_message(chat_id, text)
            delivered += 1
        except Exception:
            metrics.increment("brief_delivery_failures")
            log.exception("brief_delivery_failed", chat_id=chat_id)

    log.info("brief_broadcast_done", subscribers=len(chat_ids), delivered=delivered)
    return delivered
