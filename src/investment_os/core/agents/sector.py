from __future__ import annotations

import datetime as dt

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp
from investment_os.domain import AnalystOpinion, EvidenceRef, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot


class SectorRotationAnalyst:
    """Where does this ticker's sector sit in the current rotation?"""

    role = "sector_rotation"
    weight = 0.6

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return (
            len(snapshot.sector_returns) >= 2 and snapshot.profile.sector in snapshot.sector_returns
        )

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        returns = snapshot.sector_returns
        sector = snapshot.profile.sector
        if sector not in returns or len(returns) < 2:
            raise AnalystError(f"{snapshot.profile.ticker}: data rotasi sektor tidak memadai")

        own = returns[sector]
        others = [value for name, value in returns.items() if name != sector]
        market_avg = sum(others) / len(others)
        edge = own - market_avg
        # A 5-percentage-point 20-day edge over the rest of the market saturates.
        score = clamp(edge / 0.05)

        ranking = sorted(returns.items(), key=lambda item: item[1], reverse=True)
        position = next(i for i, (name, _) in enumerate(ranking, start=1) if name == sector)
        leaders = " > ".join(f"{name} {value * 100:+.1f}%" for name, value in ranking[:3])

        evidence = [
            EvidenceRef(
                source="market-data",
                ref_id=f"sector-rotation-{snapshot.as_of.date().isoformat()}",
                summary=f"Return 20 hari per sektor: {leaders}"
                + (" ..." if len(ranking) > 3 else ""),
                published_at=dt.datetime.combine(
                    snapshot.bars[-1].date if snapshot.bars else snapshot.as_of.date(),
                    dt.time(16, 0),
                    tzinfo=dt.UTC,
                ),
                reliability=0.85,
            )
        ]

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=[
                f"Sektor {sector} peringkat {position}/{len(ranking)} "
                f"(20 hari: {own * 100:+.1f}% vs pasar {market_avg * 100:+.1f}%)",
            ],
            evidence=evidence,
            confidence=0.6,
            caveats=(
                ["Peta rotasi dihitung dari universe terbatas, bukan seluruh bursa"]
                if len(returns) < 5
                else []
            ),
        )
