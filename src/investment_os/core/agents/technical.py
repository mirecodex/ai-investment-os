from __future__ import annotations

import datetime as dt

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp, rsi, sma
from investment_os.domain import AnalystOpinion, EvidenceRef, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot


class TechnicalAnalyst:
    role = "technical"
    weight = 1.0

    def __init__(self, fast: int = 20, slow: int = 50, rsi_period: int = 14) -> None:
        self._fast = fast
        self._slow = slow
        self._rsi_period = rsi_period

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return len(snapshot.bars) >= self._slow

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        closes = [bar.close for bar in snapshot.bars]
        if len(closes) < self._slow:
            raise AnalystError(f"{snapshot.profile.ticker}: butuh {self._slow} bar harga")

        fast_ma = sma(closes, self._fast)
        slow_ma = sma(closes, self._slow)
        momentum_pct = (closes[-1] / closes[-self._fast] - 1.0) * 100
        rsi_value = rsi(closes, self._rsi_period)
        assert fast_ma is not None and slow_ma is not None

        trend = clamp((fast_ma - slow_ma) / slow_ma * 12)
        momentum = clamp(momentum_pct / 10)
        score = clamp(0.6 * trend + 0.4 * momentum)

        key_points = [
            f"MA{self._fast} {'di atas' if fast_ma >= slow_ma else 'di bawah'} MA{self._slow} "
            f"({fast_ma:,.0f} vs {slow_ma:,.0f})",
            f"Momentum {self._fast} hari: {momentum_pct:+.1f}%",
        ]
        caveats: list[str] = []
        if rsi_value is not None:
            key_points.append(f"RSI({self._rsi_period}): {rsi_value:.0f}")
            if rsi_value >= 70 and score > 0:
                score = clamp(score * 0.5)
                caveats.append("RSI jenuh beli — ruang kenaikan jangka pendek terbatas")
            elif rsi_value <= 30 and score < 0:
                score = clamp(score * 0.5)
                caveats.append("RSI jenuh jual — tekanan turun mungkin mereda")

        last_bar = snapshot.bars[-1]
        evidence = [
            EvidenceRef(
                source="market-data",
                ref_id=f"{snapshot.profile.ticker}-ohlcv-{last_bar.date.isoformat()}",
                summary=(
                    f"Close {last_bar.close:,.0f} ({last_bar.date.isoformat()}), "
                    f"MA{self._fast}/MA{self._slow} {fast_ma:,.0f}/{slow_ma:,.0f}"
                ),
                published_at=dt.datetime.combine(last_bar.date, dt.time(16, 0), tzinfo=dt.UTC),
                reliability=0.9,
            )
        ]

        sample_ratio = min(1.0, len(closes) / (self._slow * 2))
        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=evidence,
            confidence=0.5 + 0.4 * sample_ratio,
            caveats=caveats,
        )
