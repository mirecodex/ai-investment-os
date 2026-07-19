from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from investment_os.core.agents import default_analysts
from investment_os.core.agents.base import Analyst
from investment_os.core.service import AnalysisService
from investment_os.domain import Verdict
from investment_os.eval.reliability import ReliabilityReport, reliability_report
from investment_os.knowledge.memory import InMemoryKnowledgeBase
from investment_os.observability import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class BacktestSample:
    ticker: str
    as_of: dt.date
    exit_date: dt.date
    verdict: Verdict
    confidence: float
    forward_return: float


@dataclass(frozen=True)
class BacktestResult:
    horizon_days: int
    samples: list[BacktestSample]
    reliability: ReliabilityReport

    @property
    def sample_count(self) -> int:
        return len(self.samples)


async def run_backtest(
    kb: InMemoryKnowledgeBase,
    *,
    horizon_days: int = 20,
    stride_days: int = 5,
    min_history: int = 60,
    analysts: list[Analyst] | None = None,
) -> BacktestResult:
    # Replay the committee at each historical date with an as-of view of the
    # knowledge base (no look-ahead), then measure the realized return
    # `horizon_days` trading bars later. Purpose: direction accuracy and
    # confidence calibration — never a promise of returns (docs/fase-5).
    samples: list[BacktestSample] = []

    for profile in kb.list_tickers():
        snapshot = kb.snapshot(profile.ticker)
        if snapshot is None:
            continue
        bars = snapshot.bars

        for index in range(min_history, len(bars) - horizon_days, stride_days):
            entry_bar = bars[index]
            exit_bar = bars[index + horizon_days]
            cutoff = dt.datetime.combine(entry_bar.date, dt.time(23, 59), tzinfo=dt.UTC)

            view = kb.as_of_view(cutoff)
            service = AnalysisService(view, analysts=analysts or default_analysts())
            result = await service.analyze(profile.ticker)
            decision = result.report.decision

            samples.append(
                BacktestSample(
                    ticker=profile.ticker,
                    as_of=entry_bar.date,
                    exit_date=exit_bar.date,
                    verdict=decision.verdict,
                    confidence=decision.confidence,
                    forward_return=exit_bar.close / entry_bar.close - 1.0,
                )
            )

    reliability = reliability_report(
        [(s.confidence, s.forward_return, s.verdict) for s in samples],
        horizon=f"{horizon_days}d",
    )
    log.info(
        "backtest_completed",
        samples=len(samples),
        directional=reliability.directional_count,
        hit_rate=reliability.overall_hit_rate,
    )
    return BacktestResult(horizon_days=horizon_days, samples=samples, reliability=reliability)
