"""Deterministic demo dataset.

The fixture file stores scenario *parameters* (drift, volatility, flow shift,
news items); price/flow series are synthesized here with a seeded RNG so the
demo stays reproducible without shipping megabytes of bars. Real market-data
pipelines replace this module entirely — everything downstream only sees the
``KnowledgeBase`` port.
"""

from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path
from typing import Any

from investment_os.domain import MacroSnapshot
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from investment_os.knowledge.ports import FundamentalSnapshot, PriceBar, TickerProfile
from investment_os.pipelines.news import NewsPipeline, RawNewsItem, SourceRegistry


def _trading_days(end: dt.date, count: int) -> list[dt.date]:
    days: list[dt.date] = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= dt.timedelta(days=1)
    return list(reversed(days))


def _synthesize_bars(spec: dict[str, Any], end: dt.date) -> list[PriceBar]:
    rng = random.Random(spec["seed"])
    days = _trading_days(end, int(spec["days"]))
    price = float(spec["start_price"])
    drift = float(spec["drift_bps"]) / 10_000
    vol = float(spec["vol_bps"]) / 10_000

    flow = spec["flow"]
    recent_days = int(flow.get("recent_days", 5))
    bars: list[PriceBar] = []
    for index, day in enumerate(days):
        change = rng.gauss(drift, vol)
        open_price = price
        close = max(1.0, price * (1 + change))
        high = max(open_price, close) * (1 + abs(rng.gauss(0, vol / 2)))
        low = min(open_price, close) * (1 - abs(rng.gauss(0, vol / 2)))
        net_flow = rng.gauss(float(flow["mean_bn"]), float(flow["std_bn"]))
        if index >= len(days) - recent_days:
            net_flow += float(flow.get("recent_shift_bn", 0.0))
        bars.append(
            PriceBar(
                date=day,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(rng.uniform(5e7, 3e8)),
                net_foreign_bn_idr=round(net_flow, 2),
            )
        )
        price = close
    return bars


def load_fixture_kb(path: Path) -> InMemoryKnowledgeBase:
    payload = json.loads(path.read_text())
    as_of = dt.datetime.fromisoformat(payload["as_of"])
    last_trading_day = _trading_days(as_of.date() - dt.timedelta(days=1), 1)[0]

    kb = InMemoryKnowledgeBase(as_of=as_of, macro=MacroSnapshot.model_validate(payload["macro"]))
    kb.set_index_change_pct(float(payload["index_change_pct"]))
    if "index_series" in payload:
        kb.set_index_bars(_synthesize_bars(payload["index_series"], last_trading_day))

    sources = SourceRegistry()
    for name, reliability in payload["sources"].items():
        sources.register(name, float(reliability))
    news_pipeline = NewsPipeline(kb, sources)

    raw_news: list[RawNewsItem] = []
    for spec in payload["tickers"]:
        profile = TickerProfile.model_validate(spec["profile"])
        bars = _synthesize_bars(spec["price_series"], last_trading_day)

        fundamentals = None
        if "fundamentals" in spec:
            fields = dict(spec["fundamentals"])
            age_days = float(fields.pop("age_days"))
            fundamentals = FundamentalSnapshot(
                ticker=profile.ticker,
                reported_at=as_of - dt.timedelta(days=age_days),
                **fields,
            )

        kb.register_ticker(profile, bars, fundamentals)

        for item in spec.get("news", []):
            raw_news.append(
                RawNewsItem(
                    source=item["source"],
                    title=item["title"],
                    body=item["body"],
                    published_at=as_of - dt.timedelta(days=float(item["days_ago"])),
                    tickers=[profile.ticker],
                    sentiment=float(item["sentiment"]),
                )
            )

    news_pipeline.ingest(raw_news, now=as_of)
    return kb
