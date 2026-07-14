"""Golden suite runner.

Each case runs the full committee (deterministic, no LLM) and is checked on
two levels:

1. Case expectations — verdict, rule triggers, confidence bounds.
2. Invariant checks applied to every case regardless of expectations,
   from the evaluation dimensions in docs/fase-5:
   - groundedness: every argument point carries evidence, and evidence
     backs the run at all unless it abstained;
   - explainability: audit trail present, headline non-empty;
   - safety: the rendered user-facing report contains the disclaimer and
     no guarantee language (rule R4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from investment_os.core.agents import default_analysts
from investment_os.core.explain import AnalysisReport
from investment_os.core.explain.guard import narrative_violations
from investment_os.core.service import AnalysisService
from investment_os.domain import Verdict
from investment_os.eval.golden import GoldenCase, GoldenSuite
from investment_os.interfaces.telegram.presenter import DISCLAIMER, render_report
from investment_os.knowledge.fixtures import load_fixture_kb


@dataclass(frozen=True)
class CaseResult:
    case: GoldenCase
    failures: list[str]
    summary: str

    @property
    def passed(self) -> bool:
        return not self.failures


async def run_suite(suite: GoldenSuite, *, repo_root: Path) -> list[CaseResult]:
    kb = load_fixture_kb(repo_root / suite.fixture)
    service = AnalysisService(kb, analysts=default_analysts())

    results: list[CaseResult] = []
    for case in suite.cases:
        outcome = await service.analyze(case.ticker)
        report = outcome.report
        failures = _check_expectations(case, report) + _check_invariants(report)
        summary = (
            f"{report.decision.verdict.value} "
            f"(proposed {report.decision.proposed_verdict.value}, "
            f"conf {report.decision.confidence:.2f} {report.decision.confidence_band}, "
            f"rules {[t.rule_id for t in report.decision.triggered_rules] or '-'})"
        )
        results.append(CaseResult(case=case, failures=failures, summary=summary))
    return results


def _check_expectations(case: GoldenCase, report: AnalysisReport) -> list[str]:
    expect = case.expect
    decision = report.decision
    failures: list[str] = []
    triggered = {t.rule_id for t in decision.triggered_rules}

    if decision.verdict is not expect.verdict:
        failures.append(f"verdict {decision.verdict.value}, diharapkan {expect.verdict.value}")
    if expect.proposed_verdict and decision.proposed_verdict is not expect.proposed_verdict:
        failures.append(
            f"proposed {decision.proposed_verdict.value}, "
            f"diharapkan {expect.proposed_verdict.value}"
        )
    for rule_id in expect.rules_include:
        if rule_id not in triggered:
            failures.append(f"rule {rule_id} diharapkan aktif tetapi tidak")
    for rule_id in expect.rules_exclude:
        if rule_id in triggered:
            failures.append(f"rule {rule_id} aktif padahal seharusnya tidak")
    if expect.confidence_min is not None and decision.confidence < expect.confidence_min:
        failures.append(f"confidence {decision.confidence:.2f} < {expect.confidence_min}")
    if expect.confidence_max is not None and decision.confidence > expect.confidence_max:
        failures.append(f"confidence {decision.confidence:.2f} > {expect.confidence_max}")
    if expect.band and decision.confidence_band != expect.band:
        failures.append(f"band {decision.confidence_band}, diharapkan {expect.band}")
    if expect.requires_review is not None and decision.requires_review != expect.requires_review:
        failures.append(f"requires_review={decision.requires_review}")
    if expect.min_evidence is not None and len(report.evidence) < expect.min_evidence:
        failures.append(f"evidence {len(report.evidence)} < {expect.min_evidence}")
    return failures


def _check_invariants(report: AnalysisReport) -> list[str]:
    failures: list[str] = []

    # Groundedness: arguments must cite evidence; non-abstain runs need some.
    for argument in (report.bull_case, report.bear_case):
        for point in argument.points:
            if not point.evidence:
                failures.append(f"klaim tanpa evidence: '{point.claim[:60]}'")
    if report.decision.verdict is not Verdict.ABSTAIN and not report.evidence:
        failures.append("rekomendasi tanpa evidence sama sekali")

    # Explainability: reconstructable reasoning.
    if not report.audit_trail:
        failures.append("audit trail kosong")
    if not report.headline.strip():
        failures.append("headline kosong")

    # Safety: rendered output carries the disclaimer, no guarantee language.
    rendered = render_report(report)
    if DISCLAIMER not in rendered:
        failures.append("disclaimer hilang dari output")
    failures.extend(
        f"safety: {violation}"
        for violation in narrative_violations(rendered, [rendered])
        # numbers always match themselves here; this isolates banned phrases
        if violation.startswith("frasa terlarang")
    )
    return failures
