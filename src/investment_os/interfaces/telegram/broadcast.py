from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from investment_os.core.service import AnalysisService
from investment_os.interfaces.telegram import presenter
from investment_os.interfaces.telegram.botapi import TelegramApiError
from investment_os.observability import get_logger, metrics
from investment_os.users.subscriptions import SubscriptionRepository

log = get_logger(__name__)

# Telegram allows ~30 messages/second across all chats; pace below that so a
# large subscriber list never trips the broadcast-wide 429.
DEFAULT_PACE_S = 0.05


class MessageSender(Protocol):
    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None: ...


async def broadcast_brief(
    sender: MessageSender,
    subscriptions: SubscriptionRepository,
    analysis: AnalysisService,
    *,
    pace_s: float = DEFAULT_PACE_S,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> int:
    """Render today's brief once, deliver to every subscriber. Returns sends."""
    chat_ids = subscriptions.chat_ids()
    if not chat_ids:
        log.info("brief_broadcast_skipped", reason="no_subscribers")
        return 0

    text = presenter.render_brief(analysis.daily_brief())
    delivered = 0
    dropped = 0
    for position, chat_id in enumerate(chat_ids):
        if position and pace_s > 0:
            await sleep(pace_s)
        try:
            await sender.send_message(chat_id, text)
            delivered += 1
        except TelegramApiError as exc:
            if exc.is_blocked:
                subscriptions.unsubscribe_chat(chat_id)
                dropped += 1
                metrics.increment("brief_subscribers_dropped")
                log.info("brief_subscriber_dropped", chat_id=chat_id, reason=exc.description)
            else:
                metrics.increment("brief_delivery_failures")
                log.exception("brief_delivery_failed", chat_id=chat_id)
        except Exception:
            metrics.increment("brief_delivery_failures")
            log.exception("brief_delivery_failed", chat_id=chat_id)

    log.info(
        "brief_broadcast_done",
        subscribers=len(chat_ids),
        delivered=delivered,
        dropped=dropped,
    )
    return delivered
