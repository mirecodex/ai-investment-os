"""End-to-end committee runs against the fixture knowledge base."""

from __future__ import annotations

import pytest

from investment_os.app.container import Container
from investment_os.core.service import TickerNotFoundError
from investment_os.domain import Verdict
from investment_os.interfaces.telegram.presenter import DISCLAIMER, render_brief, render_report


async def test_conflicting_signals_force_hold_via_r1(container: Container) -> None:
    """ANTM fixture: strong fundamentals, negative news, heavy foreign selling."""
    result = await container.analysis.analyze("ANTM")
    decision = result.report.decision

    assert decision.verdict is Verdict.HOLD
    assert any(t.rule_id in ("R1", "R1b") for t in decision.triggered_rules)
    assert result.report.evidence, "every recommendation must carry evidence"
    assert [e.node for e in result.report.audit_trail][:3] == [
        "load_context",
        "route_analysts",
        "run_analysts",
    ]


async def test_aligned_signals_produce_buy(container: Container) -> None:
    """BBCA fixture: uptrend, positive news, foreign accumulation, solid fundamentals."""
    result = await container.analysis.analyze("BBCA")
    decision = result.report.decision

    assert decision.verdict is Verdict.BUY
    assert decision.proposed_verdict is Verdict.BUY
    assert result.report.bull_case.strength > result.report.bear_case.strength
    assert 0.0 < decision.confidence <= 1.0


async def test_unknown_ticker_raises(container: Container) -> None:
    with pytest.raises(TickerNotFoundError):
        await container.analysis.analyze("ZZZZ")


async def test_report_rendering_includes_disclaimer(container: Container) -> None:
    result = await container.analysis.analyze("TLKM")
    text = render_report(result.report)
    assert "TLKM" in text
    assert DISCLAIMER in text

    brief_text = render_brief(container.analysis.daily_brief())
    assert "Market Brief" in brief_text
    assert DISCLAIMER in brief_text


async def test_router_handles_full_conversation(container: Container) -> None:
    router = container.router
    assert "asisten riset" in (await router.handle("u1", "/start")).text

    reply = await router.handle("u1", "/analyze BBCA")
    assert "BBCA" in reply.text and "Keputusan" in reply.text

    assert "Format" in (await router.handle("u1", "/analyze not-a-ticker")).text
    assert "belum tercakup" in (await router.handle("u1", "/analyze ZZZZ")).text

    assert "ditambahkan" in (await router.handle("u1", "/add BBCA")).text
    assert "sudah ada" in (await router.handle("u1", "/add BBCA")).text
    assert "BBCA" in (await router.handle("u1", "/watchlist")).text
    assert "dihapus" in (await router.handle("u1", "/remove BBCA")).text
    assert "kosong" in (await router.handle("u1", "/watchlist")).text
