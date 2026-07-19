from __future__ import annotations

import asyncio
from typing import Any

import httpx

from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class TelegramApiError(RuntimeError):
    def __init__(self, method: str, status: int, description: str) -> None:
        super().__init__(f"{method} -> HTTP {status}: {description}")
        self.method = method
        self.status = status
        self.description = description

    @property
    def is_blocked(self) -> bool:
        # 403: the user blocked the bot or removed it from the chat. Permanent
        # for that chat_id — callers should drop the subscription, not retry.
        return self.status == 403

    @property
    def is_auth_failure(self) -> bool:
        return self.status in (401, 404)


class TelegramClient:
    def __init__(
        self,
        token: str,
        *,
        poll_timeout_s: int = 30,
        max_attempts: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._poll_timeout_s = poll_timeout_s
        self._max_attempts = max_attempts
        self._http = httpx.AsyncClient(timeout=poll_timeout_s + 10, transport=transport)

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
        try:
            await self._call(
                "sendMessage",
                {"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
        except TelegramApiError as exc:
            # A markup bug must degrade to plain text, not lose the message.
            if exc.status != 400 or "can't parse entities" not in exc.description:
                raise
            metrics.increment("telegram_parse_mode_fallbacks")
            log.warning("telegram_parse_mode_fallback", chat_id=chat_id, error=exc.description)
            await self._call("sendMessage", {"chat_id": chat_id, "text": text})
        metrics.increment("telegram_messages_sent")

    async def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        delay = 1.0
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._http.post(f"{self._base}/{method}", json=params)
            except httpx.TransportError as exc:
                if attempt == self._max_attempts:
                    raise
                log.warning("telegram_call_retry", method=method, attempt=attempt, error=repr(exc))
                await asyncio.sleep(delay)
                delay *= 2
                continue

            data = self._parse_body(response)
            if response.status_code < 400 and data.get("ok", False):
                return data

            status = response.status_code
            description = str(data.get("description") or response.reason_phrase or "unknown")
            if status not in _RETRYABLE_STATUS or attempt == self._max_attempts:
                raise TelegramApiError(method, status, description)

            # On 429 Telegram tells us exactly how long to back off.
            parameters = data.get("parameters") or {}
            wait_s = max(float(parameters.get("retry_after", 0.0)), delay)
            log.warning(
                "telegram_call_retry",
                method=method,
                attempt=attempt,
                status=status,
                wait_s=wait_s,
            )
            await asyncio.sleep(wait_s)
            delay *= 2
        raise RuntimeError("unreachable")

    @staticmethod
    def _parse_body(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}
