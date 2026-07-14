from __future__ import annotations

import asyncio
import datetime as dt
import json
from pathlib import Path

from pydantic import BaseModel, Field

from investment_os.domain import MacroSnapshot
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from investment_os.knowledge.ports import TickerProfile
from investment_os.observability import get_logger
from investment_os.pipelines.market import PriceFeed, PriceFeedError
from investment_os.pipelines.news import NewsPipeline, RawNewsItem, SourceRegistry
from investment_os.pipelines.rss import FeedSpec, RssCrawler, TickerTagger

log = get_logger(__name__)


class UniverseTicker(BaseModel):
    ticker: str
    name: str
    sector: str
    aliases: list[str] = Field(default_factory=list)


class UniverseConfig(BaseModel):
    macro: MacroSnapshot
    sources: dict[str, float]
    feeds: list[FeedSpec] = Field(default_factory=list)
    tickers: list[UniverseTicker]

    @classmethod
    def load(cls, path: Path) -> UniverseConfig:
        return cls.model_validate(json.loads(path.read_text()))

    def tagger(self) -> TickerTagger:
        return TickerTagger({t.ticker: t.aliases for t in self.tickers})


async def build_live_kb(
    universe: UniverseConfig,
    price_feed: PriceFeed,
    news_items: list[RawNewsItem],
    *,
    history_days: int = 120,
    now: dt.datetime | None = None,
) -> InMemoryKnowledgeBase:
    now = now or dt.datetime.now(tz=dt.UTC)
    kb = InMemoryKnowledgeBase(as_of=now, macro=universe.macro)

    try:
        index_bars = await price_feed.index_bars(days=history_days)
        kb.set_index_bars(index_bars)
        if len(index_bars) >= 2:
            kb.set_index_change_pct((index_bars[-1].close / index_bars[-2].close - 1.0) * 100)
    except PriceFeedError as exc:
        log.warning("index_fetch_failed", error=repr(exc))

    async def register(spec: UniverseTicker) -> str | None:
        try:
            bars = await price_feed.daily_bars(spec.ticker, days=history_days)
        except PriceFeedError as exc:
            log.warning("ticker_fetch_failed", ticker=spec.ticker, error=repr(exc))
            return None
        if not bars:
            log.warning("ticker_empty", ticker=spec.ticker)
            return None
        kb.register_ticker(
            TickerProfile(ticker=spec.ticker, name=spec.name, sector=spec.sector), bars
        )
        return spec.ticker

    registered = [
        ticker
        for ticker in await asyncio.gather(*(register(spec) for spec in universe.tickers))
        if ticker is not None
    ]

    registry = SourceRegistry()
    for source, reliability in universe.sources.items():
        registry.register(source, reliability)
    NewsPipeline(kb, registry).ingest(news_items, now=now)

    log.info("live_kb_built", tickers=len(registered), news=len(news_items))
    return kb


async def load_live_kb(universe_path: Path, *, history_days: int = 120) -> InMemoryKnowledgeBase:
    """Convenience wiring for the CLI/bot: Yahoo prices + RSS news."""
    from investment_os.pipelines.market import YahooPriceFeed

    universe = UniverseConfig.load(universe_path)
    feed = YahooPriceFeed()
    crawler = RssCrawler(universe.feeds, universe.tagger())
    try:
        news = await crawler.collect()
        return await build_live_kb(universe, feed, news, history_days=history_days)
    finally:
        await crawler.close()
        await feed.close()
