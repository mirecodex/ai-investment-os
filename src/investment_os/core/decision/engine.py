from __future__ import annotations

from dataclasses import dataclass

from investment_os.core.decision.rules import DecisionFacts, EffectKind, Rule, default_rules
from investment_os.domain import RuleTrigger, Verdict
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


@dataclass(frozen=True)
class RuleOutcome:
    verdict: Verdict
    triggers: list[RuleTrigger]
    requires_review: bool

    @property
    def overridden(self) -> bool:
        return any(t.effect.startswith(("FORCE", "CAP")) for t in self.triggers)


class DecisionEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        catalog = rules if rules is not None else default_rules()
        self._rules = sorted(catalog, key=lambda r: r.priority)

    def evaluate(self, proposed: Verdict, facts: DecisionFacts) -> RuleOutcome:
        verdict = proposed
        forced = False
        requires_review = False
        triggers: list[RuleTrigger] = []

        for rule in self._rules:
            if not rule.applies(facts):
                continue

            if rule.effect.kind is EffectKind.FORCE and not forced:
                assert rule.effect.verdict is not None
                if rule.effect.verdict != verdict:
                    triggers.append(_trigger(rule, f"FORCE {verdict}->{rule.effect.verdict}"))
                else:
                    triggers.append(_trigger(rule, f"FORCE {rule.effect.verdict} (confirmed)"))
                verdict = rule.effect.verdict
                forced = True

            elif rule.effect.kind is EffectKind.CAP_BULLISH and not forced:
                cap = rule.effect.verdict
                assert cap is not None
                if verdict.bullishness > cap.bullishness:
                    triggers.append(_trigger(rule, f"CAP {verdict}->{cap}"))
                    verdict = cap

            elif rule.effect.kind is EffectKind.FLAG_REVIEW:
                requires_review = True
                triggers.append(_trigger(rule, "FLAG_REVIEW"))

        outcome = RuleOutcome(verdict=verdict, triggers=triggers, requires_review=requires_review)
        if outcome.overridden:
            metrics.increment("decision_rule_overrides")
            log.info(
                "decision_overridden",
                proposed=proposed.value,
                final=verdict.value,
                rules=[t.rule_id for t in triggers],
            )
        return outcome


def _trigger(rule: Rule, effect: str) -> RuleTrigger:
    return RuleTrigger(rule_id=rule.rule_id, reason=rule.reason, effect=effect)
