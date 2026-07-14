from __future__ import annotations

import datetime as dt

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp, zscore
from investment_os.domain import AnalystOpinion, EvidenceRef, FlowRegime, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot


def classify_flow(z: float) -> FlowRegime:
    if z <= -1.5:
        return FlowRegime.HEAVY_SELL
    if z <= -0.5:
        return FlowRegime.SELL
    if z >= 1.5:
        return FlowRegime.HEAVY_BUY
    if z >= 0.5:
        return FlowRegime.BUY
    return FlowRegime.BALANCED


class ForeignFlowAnalyst:
    role = "foreign_flow"
    weight = 0.9

    def __init__(self, window: int = 60, recent: int = 5) -> None:
        self._window = window
        self._recent = recent

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return len(snapshot.bars) >= self._recent * 4

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        flows = [bar.net_foreign_bn_idr for bar in snapshot.bars][-self._window :]
        if len(flows) < self._recent * 4:
            raise AnalystError(f"{snapshot.profile.ticker}: riwayat foreign flow terlalu pendek")

        recent_avg = sum(flows[-self._recent :]) / self._recent
        z = zscore(flows[: -self._recent], recent_avg)
        if z is None:
            raise AnalystError(f"{snapshot.profile.ticker}: baseline flow tidak memadai")

        regime = classify_flow(z)
        score = clamp(z / 2.5)
        recent_total = sum(flows[-self._recent :])

        last_bar = snapshot.bars[-1]
        evidence = [
            EvidenceRef(
                source="foreign-flow",
                ref_id=f"{snapshot.profile.ticker}-flow-{last_bar.date.isoformat()}",
                summary=(
                    f"Net foreign {self._recent} hari: {recent_total:+,.0f} miliar IDR "
                    f"(z-score {z:+.2f} vs baseline {self._window} hari)"
                ),
                published_at=dt.datetime.combine(last_bar.date, dt.time(16, 0), tzinfo=dt.UTC),
                reliability=0.9,
            )
        ]

        regime_label = {
            FlowRegime.HEAVY_SELL: "distribusi asing berat",
            FlowRegime.SELL: "tekanan jual asing",
            FlowRegime.BALANCED: "flow asing seimbang",
            FlowRegime.BUY: "akumulasi asing",
            FlowRegime.HEAVY_BUY: "akumulasi asing agresif",
        }[regime]

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=[
                f"Regime: {regime_label} (z {z:+.2f})",
                f"Akumulasi {self._recent} hari terakhir: {recent_total:+,.0f} miliar IDR",
            ],
            evidence=evidence,
            confidence=0.8,
            caveats=["Flow asing paling informatif untuk emiten big-cap"],
            signals={"flow_regime": regime.value},
        )
