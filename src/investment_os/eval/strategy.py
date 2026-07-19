from __future__ import annotations

import bisect
import datetime as dt
from dataclasses import dataclass

from investment_os.domain import Verdict
from investment_os.eval.backtest import BacktestSample
from investment_os.knowledge.ports import PriceBar


@dataclass(frozen=True)
class StrategyRound:
    entry: dt.date
    exit: dt.date
    positions: int
    strategy_return: float
    index_return: float | None


@dataclass(frozen=True)
class StrategyReport:
    rounds: list[StrategyRound]
    strategy_total: float
    index_total: float | None
    max_drawdown: float

    @property
    def round_count(self) -> int:
        return len(self.rounds)


def strategy_report(
    samples: list[BacktestSample], index_bars: list[PriceBar] | None = None
) -> StrategyReport:
    """Paper portfolio over replayed BUY decisions.

    Equal weight across BUYs sharing an entry date; windows never overlap
    (capital sits in one round at a time), so compounding is honest. The
    index leg holds IHSG over exactly the same windows — a fair benchmark,
    not buy-and-hold over the whole period. Calibration evidence only,
    never a performance promise.
    """
    buys: dict[dt.date, list[BacktestSample]] = {}
    for sample in samples:
        if sample.verdict is Verdict.BUY:
            buys.setdefault(sample.as_of, []).append(sample)

    index_dates = [bar.date for bar in index_bars] if index_bars else []
    rounds: list[StrategyRound] = []
    equity = 1.0
    index_equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    cursor = dt.date.min
    index_covered = True

    for entry in sorted(buys):
        if entry < cursor:
            continue  # capital still deployed in the previous round
        batch = buys[entry]
        exit_ = max(sample.exit_date for sample in batch)
        period = sum(sample.forward_return for sample in batch) / len(batch)

        index_return = _index_window_return(index_bars or [], index_dates, entry, exit_)
        if index_return is None:
            index_covered = False
        else:
            index_equity *= 1.0 + index_return

        equity *= 1.0 + period
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1.0 - equity / peak)
        rounds.append(
            StrategyRound(
                entry=entry,
                exit=exit_,
                positions=len(batch),
                strategy_return=period,
                index_return=index_return,
            )
        )
        cursor = exit_

    return StrategyReport(
        rounds=rounds,
        strategy_total=equity - 1.0,
        index_total=(index_equity - 1.0) if rounds and index_covered and index_dates else None,
        max_drawdown=max_drawdown,
    )


def _index_window_return(
    index_bars: list[PriceBar], dates: list[dt.date], entry: dt.date, exit_: dt.date
) -> float | None:
    if not index_bars:
        return None
    start = bisect.bisect_right(dates, entry) - 1
    end = bisect.bisect_right(dates, exit_) - 1
    if start < 0 or end <= start:
        return None
    entry_close = index_bars[start].close
    return index_bars[end].close / entry_close - 1.0 if entry_close > 0 else None
