from __future__ import annotations

import datetime as dt
import math
from itertools import pairwise

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp
from investment_os.domain import AnalystOpinion, EvidenceRef, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot

_TRADING_DAYS = 252


def _daily_returns(closes: list[float]) -> list[float]:
    return [curr / prev - 1.0 for prev, curr in pairwise(closes)]


class QuantAnalyst:
    """Risk-adjusted view: volatility, Sharpe-style momentum, beta vs IHSG."""

    role = "quant"
    weight = 0.8

    def __init__(self, window: int = 60, min_bars: int = 40) -> None:
        self._window = window
        self._min_bars = min_bars

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return len(snapshot.bars) >= self._min_bars

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        closes = [bar.close for bar in snapshot.bars][-self._window :]
        returns = _daily_returns(closes)
        if len(returns) < self._min_bars - 1:
            raise AnalystError(f"{snapshot.profile.ticker}: riwayat return terlalu pendek")

        mean_daily = sum(returns) / len(returns)
        variance = sum((r - mean_daily) ** 2 for r in returns) / (len(returns) - 1)
        daily_std = math.sqrt(variance)
        annual_vol = daily_std * math.sqrt(_TRADING_DAYS)
        sharpe = (mean_daily / daily_std) * math.sqrt(_TRADING_DAYS) if daily_std > 1e-9 else 0.0

        # Risk-adjusted momentum drives the stance; a Sharpe of ±2 saturates.
        score = clamp(sharpe / 2.0)

        key_points = [
            f"Volatilitas tahunan {annual_vol * 100:.0f}% · risk-adjusted momentum {sharpe:+.2f}",
        ]
        caveats: list[str] = []

        beta = self._beta(snapshot, returns)
        if beta is not None:
            key_points.append(f"Beta vs IHSG: {beta:.2f}")
            if beta > 1.3:
                caveats.append(f"Beta tinggi ({beta:.2f}) — sensitif terhadap koreksi pasar")
        if annual_vol > 0.45:
            score = clamp(score * 0.6)
            caveats.append(f"Volatilitas sangat tinggi ({annual_vol * 100:.0f}% p.a.)")

        last_bar = snapshot.bars[-1]
        evidence = [
            EvidenceRef(
                source="market-data",
                ref_id=f"{snapshot.profile.ticker}-quant-{last_bar.date.isoformat()}",
                summary=(
                    f"{len(returns)} return harian: vol {annual_vol * 100:.0f}% p.a., "
                    f"momentum {sharpe:+.2f}" + (f", beta {beta:.2f}" if beta is not None else "")
                ),
                published_at=dt.datetime.combine(last_bar.date, dt.time(16, 0), tzinfo=dt.UTC),
                reliability=0.9,
            )
        ]

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=evidence,
            confidence=0.7,
            caveats=caveats,
        )

    def _beta(self, snapshot: MarketSnapshot, stock_returns: list[float]) -> float | None:
        index_closes = {bar.date: bar.close for bar in snapshot.index_bars}
        if len(index_closes) < self._min_bars:
            return None

        # Align by date so holidays/halts don't skew covariance.
        paired: list[tuple[float, float]] = []
        prev_stock: float | None = None
        prev_index: float | None = None
        for bar in snapshot.bars[-self._window :]:
            index_close = index_closes.get(bar.date)
            if index_close is None:
                continue
            if prev_stock is not None and prev_index is not None:
                paired.append((bar.close / prev_stock - 1.0, index_close / prev_index - 1.0))
            prev_stock, prev_index = bar.close, index_close

        if len(paired) < self._min_bars - 1:
            return None
        mean_s = sum(s for s, _ in paired) / len(paired)
        mean_i = sum(i for _, i in paired) / len(paired)
        cov = sum((s - mean_s) * (i - mean_i) for s, i in paired) / (len(paired) - 1)
        var_i = sum((i - mean_i) ** 2 for _, i in paired) / (len(paired) - 1)
        if var_i < 1e-12:
            return None
        return cov / var_i
