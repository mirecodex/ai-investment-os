from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Protocol

import httpx

from investment_os.interfaces.telegram.botapi import TelegramApiError
from investment_os.interfaces.telegram.router import CommandRouter
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_MAX_POLL_BACKOFF_S = 300.0


class BotTransport(Protocol):
    async def get_updates(self, offset: int | None) -> list[dict[str, Any]]: ...

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None: ...


async def run_polling(
    client: BotTransport, router: CommandRouter, *, retry_base_s: float = 1.0
) -> None:
    offset: int | None = None
    backoff = retry_base_s
    log.info("telegram_polling_started")
    while True:
        try:
            updates = await client.get_updates(offset)
        except TelegramApiError as exc:
            if exc.is_auth_failure:
                # Bad token: retrying forever would only hide a config error.
                raise
            backoff = await _poll_backoff(backoff, exc)
            continue
        except httpx.TransportError as exc:
            backoff = await _poll_backoff(backoff, exc)
            continue

        backoff = retry_base_s
        for update in updates:
            offset = update["update_id"] + 1
            await _handle_update(client, router, update)


async def _handle_update(
    client: BotTransport, router: CommandRouter, update: dict[str, Any]
) -> None:
    message = update.get("message") or {}
    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return
    try:
        reply = await router.handle(str(chat_id), text)
        await client.send_message(chat_id, reply.text, parse_mode=reply.parse_mode)
    except Exception:
        log.exception("update_handling_failed", chat_id=chat_id)
        with contextlib.suppress(Exception):
            await client.send_message(
                chat_id,
                "Maaf, terjadi kendala saat memproses permintaan. Coba lagi sebentar.",
                parse_mode="HTML",
            )


async def _poll_backoff(current: float, exc: Exception) -> float:
    metrics.increment("telegram_poll_failures")
    log.warning("telegram_poll_retry", error=repr(exc), wait_s=current)
    await asyncio.sleep(current)
    return min(current * 2, _MAX_POLL_BACKOFF_S)
