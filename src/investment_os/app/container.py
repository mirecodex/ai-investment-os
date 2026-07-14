"""Composition root: the only module allowed to know about everything.

Core stays interface-free and provider-free; this is where concrete
implementations (fixture KB today, Postgres/vector tomorrow; heuristic
analysts today, LLM-backed tomorrow) get wired together.
"""

from __future__ import annotations

from dataclasses import dataclass

from investment_os.config import Settings
from investment_os.core.agents import default_analysts
from investment_os.core.alerts import AlertStateStore
from investment_os.core.explain.narrator import Narrator
from investment_os.core.llm import LLMError
from investment_os.core.ports import RecommendationStore
from investment_os.core.service import AnalysisService
from investment_os.data import (
    Database,
    SqliteAlertState,
    SqliteRecommendationStore,
    SqliteSubscriptions,
    SqliteWatchlist,
)
from investment_os.interfaces.telegram.router import CommandRouter
from investment_os.knowledge.fixtures import load_fixture_kb
from investment_os.knowledge.ports import KnowledgeBase
from investment_os.llm import resolve_llm
from investment_os.llm.promptstore import PromptStore
from investment_os.observability import get_logger
from investment_os.users.subscriptions import SubscriptionRepository
from investment_os.users.watchlist import WatchlistRepository


@dataclass(frozen=True)
class Container:
    settings: Settings
    kb: KnowledgeBase
    db: Database
    analysis: AnalysisService
    watchlist: WatchlistRepository
    subscriptions: SubscriptionRepository
    recommendations: RecommendationStore
    alert_state: AlertStateStore
    router: CommandRouter


def build_container(settings: Settings, *, kb: KnowledgeBase | None = None) -> Container:
    """Wire the application; pass a prebuilt ``kb`` for live mode (async load)."""
    if kb is None:
        kb = load_fixture_kb(settings.fixtures_path)

    db = Database(settings.database_path)
    recommendations = SqliteRecommendationStore(db)
    watchlist = SqliteWatchlist(db)
    subscriptions = SqliteSubscriptions(db)
    alert_state = SqliteAlertState(db)

    narrator = _build_narrator(settings)

    analysis = AnalysisService(
        kb,
        analysts=default_analysts(),
        min_evidence=settings.analysis_min_evidence,
        stale_after_days=settings.analysis_stale_after_days,
        low_confidence_threshold=settings.low_confidence_threshold,
        recommendation_store=recommendations,
        narrator=narrator,
    )

    router = CommandRouter(analysis, watchlist, subscriptions)
    return Container(
        settings=settings,
        kb=kb,
        db=db,
        analysis=analysis,
        watchlist=watchlist,
        subscriptions=subscriptions,
        recommendations=recommendations,
        alert_state=alert_state,
        router=router,
    )


def _build_narrator(settings: Settings) -> Narrator | None:
    log = get_logger(__name__)
    if settings.llm_provider in ("off", "none", "disabled"):
        return None
    try:
        llm = resolve_llm(settings.llm_provider, settings.llm_model)
    except LLMError as exc:
        # A broken LLM config degrades to deterministic output, never a crash.
        log.warning("llm_setup_failed", error=str(exc))
        return None
    if llm is None:
        log.info("llm_disabled", reason="no provider API key configured")
        return None
    return Narrator(llm, PromptStore(settings.prompts_path), max_tokens=settings.llm_max_tokens)
