from __future__ import annotations

import asyncio
from typing import Any

import httpx

from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


class TelegramClient:
    def __init__(self, token: str, *, poll_timeout_s: int = 30) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._poll_timeout_s = poll_timeout_s
        self._http = httpx.AsyncClient(timeout=poll_timeout_s + 10)

    async def close(self) -> None:
        await self._http.aclose()

    async def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": self._poll_timeout_s}
        if offset is not None:
            params["offset"] = offset
        payload = await self._call("getUpdates", params)
        result = payload.get("result", [])
        return result if isinstance(result, list) else []

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str = "HTML") -> None:
        await self._call(
            "sendMessage",
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        )
        metrics.increment("telegram_messages_sent")

    async def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        delay = 1.0
        for attempt in range(4):
            try:
                response = await self._http.post(f"{self._base}/{method}", json=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                if not data.get("ok", False):
                    raise RuntimeError(f"Telegram API error: {data.get('description')}")
                return data
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt == 3:
                    raise
                log.warning("telegram_call_retry", method=method, attempt=attempt, error=repr(exc))
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")
