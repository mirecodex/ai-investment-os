from __future__ import annotations

import json
from pathlib import Path

from investment_os.app.container import Container, build_container
from investment_os.config import Settings
from investment_os.core.agents import LlmNewsAnalyst, NewsAnalyst
from investment_os.core.llm import LLMError, LLMRequest, LLMResponse
from investment_os.domain import MarketBrief, Stance
from investment_os.knowledge.fixtures import load_fixture_kb
from investment_os.llm.promptstore import PromptStore
from tests.conftest import FIXTURE_PATH, NOW

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


class ScriptedLLM:
    provider = "fake"
    model = "fake-1"

    def __init__(self, text: str | Exception) -> None:
        self._text = text
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if isinstance(self._text, Exception):
            raise self._text
        return LLMResponse(
            text=self._text,
            provider=self.provider,
            model=self.model,
            input_tokens=1,
            output_tokens=1,
        )

    async def close(self) -> None:
        return None


def brief() -> MarketBrief:
    return MarketBrief(
        date=NOW.date(),
        sentiment=Stance.NEUTRAL,
        score=0.0,
        confidence=0.5,
        index_change_pct=0.1,
        net_foreign_flow_bn_idr=0.0,
        highlights=[],
        macro=load_fixture_kb(FIXTURE_PATH).macro(),
    )


def make_analyst(llm: ScriptedLLM) -> LlmNewsAnalyst:
    return LlmNewsAnalyst(llm, PromptStore(PROMPTS), fallback=NewsAnalyst())


async def test_grounded_response_becomes_opinion() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None and snapshot.news
    ref = snapshot.news[0].ref_id

    llm = ScriptedLLM(
        json.dumps(
            {
                "score": 0.6,
                "confidence": 0.7,
                "key_points": ["Pemberitaan didominasi kabar kinerja yang solid."],
                "caveats": ["Valuasi sudah premium."],
                "evidence_refs": [ref, ref],
            }
        )
    )
    opinion = await make_analyst(llm).assess(snapshot, brief())

    assert opinion.role == "news"
    assert opinion.score == 0.6
    assert [e.ref_id for e in opinion.evidence] == [ref]  # deduped, all grounded
    assert opinion.signals["engine"] == "llm"
    assert opinion.signals["llm_version"] == "fake/fake-1"
    # The rendered prompt must carry the curated items, nothing else.
    assert ref in llm.requests[0].prompt


async def test_prompt_never_leaks_beyond_curated_items() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None
    llm = ScriptedLLM(LLMError("down"))
    await make_analyst(llm).assess(snapshot, brief())

    prompt = llm.requests[0].prompt
    for item in snapshot.news:
        assert item.title in prompt
    assert "http" not in prompt  # source URLs stay out of the model's view


async def test_hallucinated_citation_falls_back_to_lexicon() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None

    llm = ScriptedLLM(
        json.dumps(
            {
                "score": -0.9,
                "confidence": 0.9,
                "key_points": ["Klaim tanpa dasar."],
                "evidence_refs": ["berita-karangan-999"],
            }
        )
    )
    opinion = await make_analyst(llm).assess(snapshot, brief())
    expected = await NewsAnalyst().assess(snapshot, brief())

    assert opinion == expected  # deterministic analyst took over wholesale


async def test_malformed_and_out_of_range_fall_back() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None
    expected = await NewsAnalyst().assess(snapshot, brief())

    for text in (
        "maaf, saya tidak bisa",
        '{"score": 3.0, "confidence": 0.5, "key_points": ["x"], "evidence_refs": ["r"]}',
        '{"score": 0.5, "confidence": 0.5, "key_points": [], "evidence_refs": ["r"]}',
        '{"score": true, "confidence": 0.5, "key_points": ["x"], "evidence_refs": ["r"]}',
    ):
        assert await make_analyst(ScriptedLLM(text)).assess(snapshot, brief()) == expected


async def test_provider_outage_falls_back() -> None:
    kb = load_fixture_kb(FIXTURE_PATH)
    snapshot = kb.snapshot("BBCA")
    assert snapshot is not None

    opinion = await make_analyst(ScriptedLLM(LLMError("provider down"))).assess(snapshot, brief())
    assert opinion == await NewsAnalyst().assess(snapshot, brief())


def test_container_stays_deterministic_without_llm(tmp_path: Path, container: Container) -> None:
    settings = Settings(
        fixtures_path=FIXTURE_PATH,
        database_path=tmp_path / "wiring.db",
        llm_provider="off",
        llm_analysts=True,  # flag alone must not switch the seat without a client
    )
    wired = build_container(settings)
    news_seats = [a for a in wired.analysis.analysts if a.role == "news"]
    assert len(news_seats) == 1
    assert isinstance(news_seats[0], NewsAnalyst)
    wired.db.close()
