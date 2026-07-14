from __future__ import annotations

import math

from investment_os.core.agents.base import AnalystError
from investment_os.core.agents.indicators import clamp
from investment_os.domain import AnalystOpinion, MarketBrief, Stance
from investment_os.knowledge.ports import MarketSnapshot


class NewsAnalyst:
    role = "news"
    weight = 1.0

    def __init__(self, half_life_days: float = 3.0, max_items: int = 10) -> None:
        self._half_life_days = half_life_days
        self._max_items = max_items

    def is_relevant(self, snapshot: MarketSnapshot) -> bool:
        return bool(snapshot.news)

    async def assess(self, snapshot: MarketSnapshot, brief: MarketBrief) -> AnalystOpinion:
        items = snapshot.news[: self._max_items]
        if not items:
            raise AnalystError(f"{snapshot.profile.ticker}: tidak ada berita terkurasi")

        weighted = 0.0
        total_weight = 0.0
        for item in items:
            age_days = max(0.0, (snapshot.as_of - item.published_at).total_seconds() / 86400)
            recency = math.pow(0.5, age_days / self._half_life_days)
            item_weight = item.importance * item.reliability * recency
            weighted += item.sentiment * item_weight
            total_weight += item_weight

        score = clamp(weighted / total_weight) if total_weight > 0 else 0.0
        top = sorted(items, key=lambda n: n.importance, reverse=True)[:3]

        negatives = sum(1 for i in items if i.sentiment < -0.2)
        positives = sum(1 for i in items if i.sentiment > 0.2)
        key_points = [
            f"{len(items)} berita relevan: {positives} positif, {negatives} negatif",
            *(f"{item.title} ({item.source})" for item in top),
        ]
        caveats: list[str] = []
        if positives and negatives:
            caveats.append("Arah pemberitaan bercampur — sentimen bisa berbalik cepat")

        # Coverage depth drives confidence; a single article is a weak signal.
        confidence = clamp(0.35 + 0.12 * len(items), 0.0, 0.9)

        return AnalystOpinion(
            role=self.role,
            stance=Stance.from_score(score),
            score=score,
            key_points=key_points,
            evidence=[item.as_evidence() for item in top],
            confidence=confidence,
            caveats=caveats,
        )
