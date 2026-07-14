"""Composition root: the only module allowed to know about everything.

Core stays interface-free and provider-free; this is where concrete
implementations (fixture KB today, Postgres/vector tomorrow; heuristic
analysts today, LLM-backed tomorrow) get wired together.
"""

from __future__ import annotations

from dataclasses import dataclass

from investment_os.config import Settings
from investment_os.core.agents import (
    ForeignFlowAnalyst,
    FundamentalAnalyst,
    NewsAnalyst,
    TechnicalAnalyst,
)
from investment_os.core.ports import RecommendationStore
from investment_os.core.service import AnalysisService
from investment_os.data import Database, SqliteRecommendationStore, SqliteWatchlist
from investment_os.interfaces.telegram.router import CommandRouter
from investment_os.knowledge.fixtures import load_fixture_kb
from investment_os.knowledge.ports import KnowledgeBase
from investment_os.users.watchlist import WatchlistRepository


@dataclass(frozen=True)
class Container:
    settings: Settings
    kb: KnowledgeBase
    db: Database
    analysis: AnalysisService
    watchlist: WatchlistRepository
    recommendations: RecommendationStore
    router: CommandRouter


def build_container(settings: Settings, *, kb: KnowledgeBase | None = None) -> Container:
    """Wire the application; pass a prebuilt ``kb`` for live mode (async load)."""
    if kb is None:
        kb = load_fixture_kb(settings.fixtures_path)

    db = Database(settings.database_path)
    recommendations = SqliteRecommendationStore(db)
    watchlist = SqliteWatchlist(db)

    analysis = AnalysisService(
        kb,
        analysts=[
            TechnicalAnalyst(),
            FundamentalAnalyst(),
            NewsAnalyst(),
            ForeignFlowAnalyst(),
        ],
        min_evidence=settings.analysis_min_evidence,
        stale_after_days=settings.analysis_stale_after_days,
        low_confidence_threshold=settings.low_confidence_threshold,
        recommendation_store=recommendations,
    )

    router = CommandRouter(analysis, watchlist)
    return Container(
        settings=settings,
        kb=kb,
        db=db,
        analysis=analysis,
        watchlist=watchlist,
        recommendations=recommendations,
        router=router,
    )
