from __future__ import annotations

import datetime as dt

from investment_os.domain import MacroSnapshot
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from investment_os.pipelines.news import NewsPipeline, RawNewsItem, SourceRegistry
from tests.conftest import NOW


def make_kb() -> InMemoryKnowledgeBase:
    return InMemoryKnowledgeBase(as_of=NOW, macro=MacroSnapshot(bi_rate_pct=5.25, usd_idr=15850))


def make_pipeline(kb: InMemoryKnowledgeBase) -> NewsPipeline:
    sources = SourceRegistry()
    sources.register("Kontan", 0.85)
    sources.register("Blog Anonim", 0.1)
    return NewsPipeline(kb, sources)


def item(title: str, body: str, *, source: str = "Kontan", days_ago: float = 1.0) -> RawNewsItem:
    return RawNewsItem(
        source=source,
        title=title,
        body=body,
        published_at=NOW - dt.timedelta(days=days_ago),
        tickers=["BBCA"],
    )


def test_exact_duplicates_are_dropped() -> None:
    kb = make_kb()
    pipeline = make_pipeline(kb)
    article = item("Laba naik", "Laba bersih tumbuh dua digit pada kuartal pertama.")
    accepted = pipeline.ingest([article, article.model_copy()])
    assert accepted == 1


def test_near_duplicates_are_dropped() -> None:
    kb = make_kb()
    pipeline = make_pipeline(kb)
    body = (
        "Laba bersih Bank Central Asia tumbuh dua digit pada kuartal pertama tahun ini "
        "ditopang ekspansi kredit korporasi dan efisiensi biaya dana."
    )
    accepted = pipeline.ingest(
        [
            item("Laba BBCA naik dua digit", body),
            item("Laba BBCA tumbuh dua digit", body),  # syndicated copy, retitled
        ]
    )
    assert accepted == 1


def test_unreliable_sources_are_rejected() -> None:
    kb = make_kb()
    pipeline = make_pipeline(kb)
    accepted = pipeline.ingest(
        [item("Rumor akuisisi", "Kabar burung menyebut akuisisi besar.", source="Blog Anonim")]
    )
    assert accepted == 0


def test_fresh_news_scores_higher_importance() -> None:
    kb = make_kb()
    pipeline = make_pipeline(kb)
    pipeline.ingest(
        [
            item(
                "Berita lama soal dividen",
                "Pembagian dividen tahun lalu telah selesai dilaksanakan perseroan.",
                days_ago=10,
            ),
            item(
                "Berita baru soal kredit",
                "Pertumbuhan kredit kuartal ini melampaui rata-rata industri perbankan.",
                days_ago=0.2,
            ),
        ],
        now=NOW,
    )
    _, _, headlines = kb.market_overview()
    assert headlines[0].title == "Berita baru soal kredit"
    assert headlines[0].importance > headlines[1].importance
