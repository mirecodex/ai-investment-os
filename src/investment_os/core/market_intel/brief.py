"""Market Intelligence Layer: the daily Market Brief.

Context comes before stock analysis (design philosophy #3): every committee
run receives the brief produced here, so a bullish stock signal is always
read against how the market itself is behaving today.
"""

from __future__ import annotations

import datetime as dt
import math

from investment_os.core.agents.indicators import clamp
from investment_os.domain import MarketBrief, Stance
from investment_os.knowledge.ports import KnowledgeBase


class MarketBriefBuilder:
    def __init__(self, kb: KnowledgeBase, *, flow_scale_bn_idr: float = 500.0) -> None:
        self._kb = kb
        self._flow_scale = flow_scale_bn_idr

    def build(self, date: dt.date) -> MarketBrief:
        index_change_pct, net_flow, headlines = self._kb.market_overview()

        index_component = clamp(index_change_pct / 2.0)
        flow_component = math.tanh(net_flow / self._flow_scale)
        news_component = (
            clamp(sum(n.sentiment * n.importance for n in headlines) / max(1, len(headlines)))
            if headlines
            else 0.0
        )
        score = clamp(0.45 * index_component + 0.35 * flow_component + 0.20 * news_component)

        # Breadth of agreement between the three signals drives brief confidence.
        components = [index_component, flow_component, news_component]
        spread = max(components) - min(components)
        confidence = clamp(0.85 - 0.35 * spread, 0.2, 0.9)

        highlights = [
            f"IHSG {index_change_pct:+.2f}% · net foreign {net_flow:+,.0f} miliar IDR",
            *(f"{n.title} ({n.source})" for n in headlines[:3]),
        ]

        return MarketBrief(
            date=date,
            sentiment=Stance.from_score(score),
            score=round(score, 4),
            confidence=round(confidence, 4),
            index_change_pct=index_change_pct,
            net_foreign_flow_bn_idr=net_flow,
            highlights=highlights,
            macro=self._kb.macro(),
        )
