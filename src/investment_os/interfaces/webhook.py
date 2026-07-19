from __future__ import annotations

import asyncio

import httpx

from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
FORMATS = ("generic", "discord", "slack")


class WebhookNotifier:
    """Posts watchlist alerts to one webhook endpoint.

    "generic" sends a structured JSON event (n8n, custom services);
    "discord" and "slack" match their incoming-webhook payload shapes.
    """

    def __init__(
        self,
        url: str,
        *,
        fmt: str = "generic",
        max_attempts: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if fmt not in FORMATS:
            raise ValueError(f"format webhook tidak dikenal: {fmt} (pilihan: {FORMATS})")
        self._url = url
        self._fmt = fmt
        self._max_attempts = max_attempts
        self._http = httpx.AsyncClient(timeout=10, transport=transport)

    async def close(self) -> None:
        await self._http.aclose()

    async def notify(self, ticker: str, changes: list[str], summary: str) -> None:
        lines = [f"🔔 {ticker} — perubahan material", *(f"• {c}" for c in changes)]
        text = "\n".join([*lines, f"Status: {summary}"])
        if self._fmt == "discord":
            payload: dict[str, object] = {"content": text}
        elif self._fmt == "slack":
            payload = {"text": text}
        else:
            payload = {
                "event": "watchlist_alert",
                "ticker": ticker,
                "changes": changes,
                "summary": summary,
                "text": text,
            }

        delay = 1.0
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._http.post(self._url, json=payload)
            except httpx.TransportError as exc:
                if attempt == self._max_attempts:
                    raise
                log.warning("webhook_retry", attempt=attempt, error=repr(exc))
                await asyncio.sleep(delay)
                delay *= 2
                continue
            if response.status_code < 400:
                metrics.increment("webhook_alerts_sent")
                return
            if response.status_code not in _RETRYABLE_STATUS or attempt == self._max_attempts:
                raise RuntimeError(f"webhook -> HTTP {response.status_code}")
            log.warning("webhook_retry", attempt=attempt, status=response.status_code)
            await asyncio.sleep(delay)
            delay *= 2
