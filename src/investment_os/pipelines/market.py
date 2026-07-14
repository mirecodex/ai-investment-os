from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any, Protocol

import httpx

from investment_os.knowledge.ports import PriceBar
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


class PriceFeedError(RuntimeError):
    pass


class PriceFeed(Protocol):
    async def daily_bars(self, symbol: str, *, days: int) -> list[PriceBar]: ...

    async def index_bars(self, *, days: int) -> list[PriceBar]: ...

    async def index_change_pct(self) -> float: ...


def parse_yahoo_chart(payload: dict[str, Any]) -> list[PriceBar]:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise PriceFeedError(str(chart["error"]))
    results = chart.get("result") or []
    if not results:
        raise PriceFeedError("payload tanpa result")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]

    bars: list[PriceBar] = []
    for i, ts in enumerate(timestamps):
        fields = [
            quote.get(key, [None] * len(timestamps))[i]
            for key in ("open", "high", "low", "close", "volume")
        ]
        if any(value is None for value in fields):
            continue  # Yahoo emits null rows for halted/partial sessions
        open_, high, low, close, volume = fields
        bars.append(
            PriceBar(
                date=dt.datetime.fromtimestamp(ts, tz=dt.UTC).date(),
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )
        )
    return bars


class YahooPriceFeed:
    _BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(
        self,
        http: httpx.AsyncClient | None = None,
        *,
        suffix: str = ".JK",
        index_symbol: str = "^JKSE",
        timeout_s: float = 15.0,
    ) -> None:
        self._http = http or httpx.AsyncClient(
            timeout=timeout_s, headers={"User-Agent": "investment-os/0.1"}
        )
        self._suffix = suffix
        self._index_symbol = index_symbol

    async def daily_bars(self, symbol: str, *, days: int) -> list[PriceBar]:
        payload = await self._fetch(f"{symbol.upper()}{self._suffix}", days)
        bars = parse_yahoo_chart(payload)
        metrics.increment("market_bars_fetched", float(len(bars)), symbol=symbol.upper())
        return bars[-days:]

    async def index_bars(self, *, days: int) -> list[PriceBar]:
        payload = await self._fetch(self._index_symbol, days)
        return parse_yahoo_chart(payload)[-days:]

    async def index_change_pct(self) -> float:
        bars = await self.index_bars(days=5)
        if len(bars) < 2:
            raise PriceFeedError("data indeks kurang dari 2 hari")
        prev, last = bars[-2].close, bars[-1].close
        return (last / prev - 1.0) * 100

    async def _fetch(self, yahoo_symbol: str, days: int) -> dict[str, Any]:
        span = "1y" if days > 120 else "6mo"
        url = f"{self._BASE}/{yahoo_symbol}"
        params = {"range": span, "interval": "1d", "events": ""}
        delay = 1.0
        for attempt in range(3):
            try:
                response = await self._http.get(url, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt == 2:
                    raise PriceFeedError(f"gagal mengambil {yahoo_symbol}: {exc!r}") from exc
                log.warning("price_fetch_retry", symbol=yahoo_symbol, attempt=attempt)
                await asyncio.sleep(delay)
                delay *= 2
        raise PriceFeedError("unreachable")

    async def close(self) -> None:
        await self._http.aclose()
