"""Bull/Bear synthesis and committee consensus.

The committee never invents claims: every argument point is lifted from an
analyst opinion and carries that opinion's evidence. Consensus weighs each
analyst by role weight times self-reported confidence, so a hesitant analyst
moves the needle less than a confident one.
"""

from __future__ import annotations

from investment_os.domain import AnalystOpinion, Argument, ArgumentPoint, Side, Verdict

BUY_THRESHOLD = 0.25
SELL_THRESHOLD = -0.25

# Opinions inside this band are "no directional view". They still shape the
# confidence engine's agreement factor, but they don't vote on direction —
# otherwise every neutral supporting analyst dilutes a strong committee
# signal toward HOLD by construction.
NEUTRAL_BAND = 0.1


def _points_for_side(opinions: list[AnalystOpinion], side: Side) -> list[ArgumentPoint]:
    wants_positive = side is Side.BULL
    points: list[ArgumentPoint] = []
    for opinion in opinions:
        aligned = opinion.score > 0.05 if wants_positive else opinion.score < -0.05
        if not aligned or not opinion.evidence:
            continue
        weight = min(1.0, abs(opinion.score) * opinion.confidence)
        headline = opinion.key_points[0] if opinion.key_points else opinion.stance.value
        points.append(
            ArgumentPoint(
                claim=f"[{opinion.role}] {headline}",
                weight=round(weight, 3),
                evidence=opinion.evidence,
            )
        )
    return sorted(points, key=lambda p: p.weight, reverse=True)


def build_case(opinions: list[AnalystOpinion], side: Side) -> Argument:
    return Argument(side=side, points=_points_for_side(opinions, side))


def consensus_score(opinions: dict[str, AnalystOpinion], role_weights: dict[str, float]) -> float:
    directional = {
        role: opinion for role, opinion in opinions.items() if abs(opinion.score) > NEUTRAL_BAND
    }
    pool = directional or opinions

    numerator = 0.0
    denominator = 0.0
    for role, opinion in pool.items():
        weight = role_weights.get(role, 1.0) * opinion.confidence
        numerator += opinion.score * weight
        denominator += weight
    return numerator / denominator if denominator > 0 else 0.0


def propose_verdict(score: float) -> Verdict:
    if score >= BUY_THRESHOLD:
        return Verdict.BUY
    if score <= SELL_THRESHOLD:
        return Verdict.SELL
    return Verdict.HOLD


def consistency_notes(opinions: dict[str, AnalystOpinion]) -> list[str]:
    notes: list[str] = []
    scores = {role: o.score for role, o in opinions.items()}
    if not scores:
        return ["Tidak ada analis yang menghasilkan opini."]

    spread = max(scores.values()) - min(scores.values())
    if spread > 1.0:
        most_bull = max(scores, key=lambda r: scores[r])
        most_bear = min(scores, key=lambda r: scores[r])
        notes.append(
            f"Perbedaan pendapat tajam: {most_bull} ({scores[most_bull]:+.2f}) "
            f"vs {most_bear} ({scores[most_bear]:+.2f})"
        )
    weak = [role for role, o in opinions.items() if o.confidence < 0.5]
    if weak:
        notes.append(f"Opini ber-confidence rendah: {', '.join(sorted(weak))}")
    return notes
