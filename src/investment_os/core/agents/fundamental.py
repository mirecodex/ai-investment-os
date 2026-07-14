from __future__ import annotations

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp
from investment_os.domain import AnalystOpinion, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot


class FundamentalAnalyst:
    role = "fundamental"
    weight = 1.2

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return snapshot.fundamentals is not None

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        f = snapshot.fundamentals
        if f is None:
            raise AnalystError(f"{snapshot.profile.ticker}: fundamental belum tersedia")

        quality = clamp((f.roe_pct - 8.0) / 12.0)
        growth = clamp(f.revenue_yoy_pct / 15.0)
        valuation = clamp((f.sector_pe_ratio - f.pe_ratio) / f.sector_pe_ratio * 2)
        leverage_penalty = clamp((f.debt_to_equity - 1.5) / 2.0, 0.0, 1.0)

        score = clamp(0.4 * quality + 0.25 * growth + 0.35 * valuation - 0.3 * leverage_penalty)

        discount_pct = (f.sector_pe_ratio - f.pe_ratio) / f.sector_pe_ratio * 100
        key_points = [
            f"ROE {f.roe_pct:.1f}% · margin bersih {f.net_margin_pct:.1f}% ({f.period})",
            f"Pendapatan tumbuh {f.revenue_yoy_pct:+.1f}% YoY",
            f"PER {f.pe_ratio:.1f}x, {'diskon' if discount_pct >= 0 else 'premium'} "
            f"{abs(discount_pct):.0f}% terhadap sektor",
        ]
        caveats: list[str] = []
        if leverage_penalty > 0:
            caveats.append(f"Leverage tinggi (DER {f.debt_to_equity:.2f})")

        report_age_days = (snapshot.as_of - f.reported_at).days
        if report_age_days > 120:
            caveats.append(f"Laporan keuangan berumur {report_age_days} hari")
        confidence = 0.9 if report_age_days <= 120 else 0.65

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=[f.as_evidence()],
            confidence=confidence,
            caveats=caveats,
        )
