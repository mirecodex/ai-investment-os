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
from investment_os.core.service import AnalysisService
from investment_os.interfaces.telegram.router import CommandRouter
from investment_os.knowledge.fixtures import load_fixture_kb
from investment_os.knowledge.ports import KnowledgeBase
from investment_os.users import InMemoryWatchlist
from investment_os.users.watchlist import WatchlistRepository


@dataclass(frozen=True)
class Container:
    settings: Settings
    kb: KnowledgeBase
    analysis: AnalysisService
    watchlist: WatchlistRepository
    router: CommandRouter


def build_container(settings: Settings) -> Container:
    kb = load_fixture_kb(settings.fixtures_path)

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
    )

    watchlist = InMemoryWatchlist()
    router = CommandRouter(analysis, watchlist)
    return Container(
        settings=settings, kb=kb, analysis=analysis, watchlist=watchlist, router=router
    )
