from __future__ import annotations

from investment_os.core.agents.indicators import clamp
from investment_os.domain import AnalystOpinion, EvidenceRef, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot

# Sector sensitivities to the macro snapshot. Deliberately coarse, documented
# placeholders until the domain-KB curation lands (docs/fase-3, Domain KB):
# commodity sectors ride commodity prices and a weak rupiah; importers and
# domestic-demand sectors suffer from a weak rupiah; banks get a mild NIM
# tailwind from higher policy rates, rate-sensitive sectors the opposite.
_COMMODITY_SECTORS = frozenset({"Pertambangan", "Energi", "Perkebunan"})
_USD_WINNERS = frozenset({"Pertambangan", "Energi", "Perkebunan"})
_USD_LOSERS = frozenset({"Konsumer", "Farmasi", "Otomotif & Konglomerasi", "Ritel"})
_RATE_WINNERS = frozenset({"Perbankan"})
_RATE_LOSERS = frozenset({"Properti", "Konsumer", "Teknologi"})

_NEUTRAL_BI_RATE = 5.5


class MacroAnalyst:
    role = "macro"
    weight = 0.7

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return True  # macro context always exists; its weight stays modest

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        macro = snapshot.macro
        sector = snapshot.profile.sector
        score = 0.0
        key_points: list[str] = []

        if sector in _COMMODITY_SECTORS and macro.commodities:
            avg_commodity = sum(macro.commodities.values()) / len(macro.commodities)
            score += clamp(avg_commodity / 5.0, -0.4, 0.4)
            moves = " · ".join(f"{k} {v:+.1f}%" for k, v in macro.commodities.items())
            key_points.append(f"Komoditas: {moves}")

        if macro.usd_idr_change_pct:
            direction = 0.0
            if sector in _USD_WINNERS:
                direction = 0.06
            elif sector in _USD_LOSERS:
                direction = -0.06
            score += clamp(direction * macro.usd_idr_change_pct, -0.3, 0.3)
            key_points.append(f"USD/IDR {macro.usd_idr:,.0f} ({macro.usd_idr_change_pct:+.1f}%)")

        rate_gap = macro.bi_rate_pct - _NEUTRAL_BI_RATE
        if abs(rate_gap) >= 0.25:
            if sector in _RATE_WINNERS:
                score += clamp(rate_gap * 0.08, -0.2, 0.2)
            elif sector in _RATE_LOSERS:
                score += clamp(-rate_gap * 0.08, -0.2, 0.2)
        key_points.append(f"BI Rate {macro.bi_rate_pct:.2f}%")

        score = clamp(score)
        evidence = [
            EvidenceRef(
                source="macro",
                ref_id=f"macro-{snapshot.as_of.date().isoformat()}",
                summary=(
                    f"BI Rate {macro.bi_rate_pct:.2f}%, USD/IDR {macro.usd_idr:,.0f} "
                    f"({macro.usd_idr_change_pct:+.1f}%)"
                    + (
                        ", komoditas "
                        + ", ".join(f"{k} {v:+.1f}%" for k, v in macro.commodities.items())
                        if macro.commodities
                        else ""
                    )
                ),
                published_at=snapshot.as_of,
                reliability=0.85,
            )
        ]

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=evidence,
            confidence=0.55,
            caveats=["Sensitivitas makro per sektor masih heuristik kasar (belum dikurasi pakar)"],
        )
