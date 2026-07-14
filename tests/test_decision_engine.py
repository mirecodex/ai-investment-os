from __future__ import annotations

from investment_os.core.decision import DecisionEngine
from investment_os.core.decision.rules import DecisionFacts
from investment_os.domain import FlowRegime, Stance, Verdict


def facts(**overrides: object) -> DecisionFacts:
    base: dict[str, object] = {
        "fundamental_stance": Stance.POSITIVE,
        "fundamental_score": 0.6,
        "news_stance": Stance.POSITIVE,
        "flow_regime": FlowRegime.BALANCED,
        "evidence_count": 8,
        "min_evidence": 3,
        "data_stale": False,
        "confidence": 0.8,
        "low_confidence_threshold": 0.6,
    }
    base.update(overrides)
    return DecisionFacts(**base)  # type: ignore[arg-type]


def test_clean_facts_leave_proposal_untouched() -> None:
    outcome = DecisionEngine().evaluate(Verdict.BUY, facts())
    assert outcome.verdict is Verdict.BUY
    assert outcome.triggers == []
    assert not outcome.requires_review


def test_r1_forces_hold_on_sentiment_fundamental_conflict() -> None:
    outcome = DecisionEngine().evaluate(
        Verdict.BUY,
        facts(news_stance=Stance.NEGATIVE, flow_regime=FlowRegime.HEAVY_SELL),
    )
    assert outcome.verdict is Verdict.HOLD
    assert [t.rule_id for t in outcome.triggers if t.effect.startswith("FORCE")] == ["R1"]


def test_r2_evidence_gating_beats_r1() -> None:
    outcome = DecisionEngine().evaluate(
        Verdict.BUY,
        facts(
            evidence_count=1,
            news_stance=Stance.NEGATIVE,
            flow_regime=FlowRegime.HEAVY_SELL,
        ),
    )
    assert outcome.verdict is Verdict.ABSTAIN
    forced = [t.rule_id for t in outcome.triggers if t.effect.startswith("FORCE")]
    assert forced[0] == "R2"


def test_stale_data_triggers_gating() -> None:
    outcome = DecisionEngine().evaluate(Verdict.BUY, facts(data_stale=True))
    assert outcome.verdict is Verdict.ABSTAIN


def test_heavy_sell_caps_buy_but_not_sell() -> None:
    engine = DecisionEngine()
    capped = engine.evaluate(
        Verdict.BUY, facts(fundamental_stance=Stance.NEUTRAL, flow_regime=FlowRegime.HEAVY_SELL)
    )
    assert capped.verdict is Verdict.HOLD
    assert any(t.effect.startswith("CAP") for t in capped.triggers)

    sell = engine.evaluate(
        Verdict.SELL, facts(fundamental_stance=Stance.NEUTRAL, flow_regime=FlowRegime.HEAVY_SELL)
    )
    assert sell.verdict is Verdict.SELL


def test_confidence_floor_flags_review_without_changing_verdict() -> None:
    outcome = DecisionEngine().evaluate(Verdict.BUY, facts(confidence=0.4))
    assert outcome.verdict is Verdict.BUY
    assert outcome.requires_review
    assert any(t.rule_id == "R3" for t in outcome.triggers)
