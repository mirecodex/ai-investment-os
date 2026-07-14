from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from investment_os.knowledge.ports import CuratedNews, KnowledgeBase
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")


class RawNewsItem(BaseModel):
    source: str
    title: str
    body: str
    published_at: dt.datetime
    tickers: list[str] = Field(default_factory=list)
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)
    url: str | None = None


@dataclass
class SourceRegistry:
    """Reliability scores per source; unknown sources get a conservative prior."""

    default_reliability: float = 0.4
    _scores: dict[str, float] = field(default_factory=dict)

    def register(self, source: str, reliability: float) -> None:
        self._scores[source.lower()] = max(0.0, min(1.0, reliability))

    def reliability(self, source: str) -> float:
        return self._scores.get(source.lower(), self.default_reliability)


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return " ".join(_WORD_RE.findall(text))


def _shingles(text: str, size: int = 3) -> set[str]:
    tokens = text.split()
    if len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class NewsPipeline:
    def __init__(
        self,
        kb: KnowledgeBase,
        sources: SourceRegistry | None = None,
        *,
        near_dup_threshold: float = 0.6,
        min_reliability: float = 0.25,
        importance_half_life_days: float = 2.0,
    ) -> None:
        self._kb = kb
        self._sources = sources or SourceRegistry()
        self._near_dup_threshold = near_dup_threshold
        self._min_reliability = min_reliability
        self._half_life_days = importance_half_life_days
        self._seen_hashes: set[str] = set()
        self._seen_shingles: list[set[str]] = []

    def ingest(self, items: list[RawNewsItem], *, now: dt.datetime | None = None) -> int:
        """Run curation over a batch; returns how many items reached the KB."""
        now = now or dt.datetime.now(tz=dt.UTC)
        accepted: list[CuratedNews] = []
        for item in sorted(items, key=lambda i: i.published_at):
            curated = self._curate(item, now)
            if curated is not None:
                accepted.append(curated)

        if accepted:
            self._kb.add_news(accepted)
        metrics.increment("news_ingested", float(len(items)))
        metrics.increment("news_accepted", float(len(accepted)))
        log.info("news_batch_processed", received=len(items), accepted=len(accepted))
        return len(accepted)

    def _curate(self, item: RawNewsItem, now: dt.datetime) -> CuratedNews | None:
        reliability = self._sources.reliability(item.source)
        if reliability < self._min_reliability:
            metrics.increment("news_rejected", reason="unreliable_source")
            return None

        normalized = _normalize_text(f"{item.title} {item.body}")
        exact_hash = hashlib.sha256(normalized.encode()).hexdigest()
        if exact_hash in self._seen_hashes:
            metrics.increment("news_rejected", reason="duplicate")
            return None

        shingles = _shingles(normalized)
        for prior in self._seen_shingles:
            if _jaccard(shingles, prior) >= self._near_dup_threshold:
                metrics.increment("news_rejected", reason="near_duplicate")
                return None

        self._seen_hashes.add(exact_hash)
        self._seen_shingles.append(shingles)

        return CuratedNews(
            ref_id=f"news-{exact_hash[:16]}",
            source=item.source,
            title=item.title.strip(),
            summary=item.body.strip()[:280],
            tickers=[t.upper() for t in item.tickers],
            published_at=item.published_at,
            sentiment=item.sentiment,
            importance=self._importance(item, reliability, now),
            reliability=reliability,
            url=item.url,
        )

    def _importance(self, item: RawNewsItem, reliability: float, now: dt.datetime) -> float:
        age_days = max(0.0, (now - item.published_at).total_seconds() / 86400)
        recency = math.pow(0.5, age_days / self._half_life_days)
        specificity = 1.0 + 0.15 * min(3, len(item.tickers))
        return round(min(1.0, reliability * recency * specificity), 4)
