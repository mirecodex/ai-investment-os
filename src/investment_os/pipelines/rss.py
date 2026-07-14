"""RSS ingestion for Indonesian financial media.

Fetch → parse (RSS 2.0 / Atom) → tag tickers via the universe's alias map →
score interim sentiment → hand ``RawNewsItem`` batches to ``NewsPipeline``,
which owns dedup and importance. Feed outages degrade to a warning; one dead
feed never blocks the batch.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

import httpx

from investment_os.observability import get_logger, metrics
from investment_os.pipelines.news import RawNewsItem
from investment_os.pipelines.sentiment import score_text

log = get_logger(__name__)

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class FeedSpec:
    source: str
    url: str


class TickerTagger:
    """Match tickers by symbol or company alias, on word boundaries only."""

    def __init__(self, aliases: dict[str, list[str]]) -> None:
        self._patterns: list[tuple[str, re.Pattern[str]]] = []
        for ticker, names in aliases.items():
            terms = sorted({ticker, *names}, key=len, reverse=True)
            joined = "|".join(re.escape(term) for term in terms)
            self._patterns.append((ticker.upper(), re.compile(rf"\b(?:{joined})\b", re.IGNORECASE)))

    def tag(self, text: str) -> list[str]:
        return [ticker for ticker, pattern in self._patterns if pattern.search(text)]


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return _TAG_STRIP_RE.sub(" ", element.text).strip()


def _parse_datetime(raw: str, fallback: dt.datetime) -> dt.datetime:
    for parser in (parsedate_to_datetime, dt.datetime.fromisoformat):
        try:
            parsed = parser(raw)
        except (ValueError, TypeError):
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed
    return fallback


def parse_feed(xml_text: str, *, now: dt.datetime) -> list[tuple[str, str, dt.datetime, str]]:
    """Return (title, body, published_at, link) tuples from RSS 2.0 or Atom."""
    root = ET.fromstring(xml_text)
    entries: list[tuple[str, str, dt.datetime, str]] = []

    for item in root.iter("item"):  # RSS 2.0
        title = _text(item.find("title"))
        if not title:
            continue
        body = _text(item.find("description"))
        published = _parse_datetime(_text(item.find("pubDate")), now)
        link = _text(item.find("link"))
        entries.append((title, body, published, link))

    for entry in root.iter(f"{_ATOM_NS}entry"):  # Atom
        title = _text(entry.find(f"{_ATOM_NS}title"))
        if not title:
            continue
        body = _text(entry.find(f"{_ATOM_NS}summary"))
        published = _parse_datetime(_text(entry.find(f"{_ATOM_NS}updated")), now)
        link_el = entry.find(f"{_ATOM_NS}link")
        link = link_el.get("href", "") if link_el is not None else ""
        entries.append((title, body, published, link))

    return entries


class RssCrawler:
    def __init__(
        self,
        feeds: list[FeedSpec],
        tagger: TickerTagger,
        http: httpx.AsyncClient | None = None,
        *,
        timeout_s: float = 15.0,
        max_age_days: float = 7.0,
    ) -> None:
        self._feeds = feeds
        self._tagger = tagger
        self._http = http or httpx.AsyncClient(
            timeout=timeout_s,
            headers={"User-Agent": "investment-os/0.1"},
            follow_redirects=True,
        )
        self._max_age_days = max_age_days

    async def collect(self, *, now: dt.datetime | None = None) -> list[RawNewsItem]:
        now = now or dt.datetime.now(tz=dt.UTC)
        batches = await asyncio.gather(*(self._collect_one(spec, now) for spec in self._feeds))
        items = [item for batch in batches for item in batch]
        log.info("rss_collected", feeds=len(self._feeds), items=len(items))
        return items

    async def _collect_one(self, spec: FeedSpec, now: dt.datetime) -> list[RawNewsItem]:
        try:
            response = await self._http.get(spec.url)
            response.raise_for_status()
            entries = parse_feed(response.text, now=now)
        except (httpx.TransportError, httpx.HTTPStatusError, ET.ParseError) as exc:
            metrics.increment("rss_feed_failures", source=spec.source)
            log.warning("rss_feed_failed", source=spec.source, error=repr(exc))
            return []

        items: list[RawNewsItem] = []
        for title, body, published, link in entries:
            if (now - published).total_seconds() > self._max_age_days * 86400:
                continue
            text = f"{title} {body}"
            items.append(
                RawNewsItem(
                    source=spec.source,
                    title=title,
                    body=body or title,
                    published_at=published,
                    tickers=self._tagger.tag(text),
                    sentiment=score_text(text),
                    url=link or None,
                )
            )
        return items

    async def close(self) -> None:
        await self._http.aclose()
