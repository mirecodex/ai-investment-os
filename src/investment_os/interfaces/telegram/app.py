"""Long-polling loop: Bot API updates in, router replies out."""

from __future__ import annotations

from investment_os.interfaces.telegram.botapi import TelegramClient
from investment_os.interfaces.telegram.router import CommandRouter
from investment_os.observability import get_logger

log = get_logger(__name__)


async def run_polling(client: TelegramClient, router: CommandRouter) -> None:
    offset: int | None = None
    log.info("telegram_polling_started")
    try:
        while True:
            updates = await client.get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                text = message.get("text")
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                if not text or chat_id is None:
                    continue
                try:
                    reply = await router.handle(str(chat_id), text)
                    await client.send_message(chat_id, reply.text, parse_mode=reply.parse_mode)
                except Exception:
                    log.exception("update_handling_failed", chat_id=chat_id)
                    await client.send_message(
                        chat_id,
                        "Maaf, terjadi kendala saat memproses permintaan. Coba lagi sebentar.",
                        parse_mode="HTML",
                    )
    finally:
        await client.close()
