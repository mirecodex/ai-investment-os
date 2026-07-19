from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from investment_os.app.container import _build_analysts
from investment_os.config import Settings
from investment_os.core.agents import CorporateActionAnalyst
from investment_os.core.agents.base import AnalystError
from investment_os.core.llm import LLMError
from investment_os.domain import MacroSnapshot
from investment_os.knowledge.ports import CuratedNews, MarketSnapshot, TickerProfile
from investment_os.llm.promptstore import PromptStore
from tests.conftest import FIXTURE_PATH, NOW
from tests.test_llm_news_analyst import ScriptedLLM, brief

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


def news(title: str, summary: str, ref_id: str = "aksi-1") -> CuratedNews:
    return CuratedNews(
        ref_id=ref_id,
        source="Kontan",
        title=title,
        summary=summary,
        tickers=["TEST"],
        published_at=NOW - dt.timedelta(days=1),
        sentiment=0.0,
        importance=0.8,
        reliability=0.85,
    )


def snapshot(items: list[CuratedNews]) -> MarketSnapshot:
    return MarketSnapshot(
        profile=TickerProfile(ticker="TEST", name="Test Corp", sector="Perbankan"),
        bars=[],
        news=items,
        fundamentals=None,
        macro=MacroSnapshot(bi_rate_pct=6.0, usd_idr=15850),
        as_of=NOW,
        index_bars=[],
        sector_returns={},
    )


def make_analyst(llm: ScriptedLLM) -> CorporateActionAnalyst:
    return CorporateActionAnalyst(llm, PromptStore(PROMPTS))


DIVIDEND = news("Test Corp umumkan dividen tunai", "Rasio pembayaran dinaikkan tahun ini.")
PLAIN = news("Laba Test Corp naik", "Kinerja kuartal membaik.", ref_id="biasa-1")


def test_relevance_gate_is_deterministic_keywords() -> None:
    analyst = make_analyst(ScriptedLLM("unused"))
    assert analyst.is_relevant(snapshot([DIVIDEND]))
    assert not analyst.is_relevant(snapshot([PLAIN]))
    assert not analyst.is_relevant(snapshot([]))


async def test_grounded_reply_becomes_opinion_with_llm_version() -> None:
    llm = ScriptedLLM(
        json.dumps(
            {
                "score": 0.5,
                "confidence": 0.65,
                "key_points": ["Dividen tunai menaikkan pengembalian kas ke pemegang saham."],
                "caveats": ["Menunggu persetujuan RUPS."],
                "evidence_refs": ["aksi-1"],
            }
        )
    )
    opinion = await make_analyst(llm).assess(snapshot([DIVIDEND, PLAIN]), brief())

    assert opinion.role == "corporate_action"
    assert [e.ref_id for e in opinion.evidence] == ["aksi-1"]
    assert opinion.signals["engine"] == "llm"
    assert opinion.signals["llm_version"] == "fake/fake-1"
    # only the corporate-action item goes to the model, not the plain news
    assert "aksi-1" in llm.requests[0].prompt
    assert "biasa-1" not in llm.requests[0].prompt


async def test_failure_recuses_instead_of_guessing() -> None:
    hallucinated = json.dumps(
        {
            "score": 0.9,
            "confidence": 0.9,
            "key_points": ["Klaim tanpa dasar."],
            "evidence_refs": ["karangan-7"],
        }
    )
    for reply in (ScriptedLLM(hallucinated), ScriptedLLM(LLMError("down"))):
        with pytest.raises(AnalystError):
            await make_analyst(reply).assess(snapshot([DIVIDEND]), brief())


def test_wiring_adds_seat_only_with_llm_enabled(tmp_path: Path) -> None:
    base = Settings(fixtures_path=FIXTURE_PATH, database_path=tmp_path / "w.db")
    fake = ScriptedLLM("unused")

    roles = [a.role for a in _build_analysts(base.model_copy(update={"llm_analysts": True}), fake)]
    assert roles.count("corporate_action") == 1
    assert roles.count("news") == 1

    off = _build_analysts(base.model_copy(update={"llm_analysts": True}), None)
    assert all(a.role != "corporate_action" for a in off)
    assert len(off) == 7  # deterministic committee untouched
