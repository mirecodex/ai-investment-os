from __future__ import annotations

from pathlib import Path

import pytest

from investment_os.app.container import Container
from investment_os.core.explain.guard import narrative_violations
from investment_os.core.explain.narrator import Narrator
from investment_os.core.llm import LLMError, LLMRequest, LLMResponse
from investment_os.llm.promptstore import PromptStore

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class ScriptedLLM:
    provider = "scripted"
    model = "scripted-1"

    def __init__(self, text: str | None) -> None:
        self._text = text
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        if self._text is None:
            raise LLMError("scripted failure")
        return LLMResponse(
            text=self._text,
            provider=self.provider,
            model=self.model,
            input_tokens=10,
            output_tokens=10,
        )

    async def close(self) -> None:
        pass


# -- numeric guard ---------------------------------------------------------------


def test_guard_accepts_numbers_present_in_sources() -> None:
    sources = ["ROE 21.4%, PER 22.5x", "Confidence 75%"]
    assert narrative_violations("ROE emiten 21,4% dengan confidence 75%.", sources) == []


def test_guard_rejects_invented_numbers() -> None:
    violations = narrative_violations(
        "Target harga 12.500 dalam 3 bulan.", ["ROE 21.4%", "3 analis"]
    )
    assert any("12500" in v for v in violations)


def test_guard_rejects_guarantee_language() -> None:
    violations = narrative_violations("Saham ini dijamin menguat.", [])
    assert any("dijamin" in v for v in violations)


def test_guard_normalizes_separators() -> None:
    assert narrative_violations("Harga 9.200 stabil.", ["Close 9,200"]) == []


# -- narrator --------------------------------------------------------------------


async def _run_narrator(container: Container, llm: ScriptedLLM) -> tuple[object, ScriptedLLM]:
    result = await container.analysis.analyze("BBCA")
    narrator = Narrator(llm, PromptStore(PROMPTS_DIR))
    outcome = await narrator.narrate(result.report, result.brief)
    return outcome, llm


async def test_narrator_attaches_clean_narrative(container: Container) -> None:
    llm = ScriptedLLM("Komite merekomendasikan BUY dengan fundamental yang solid.")
    outcome, llm = await _run_narrator(container, llm)

    assert outcome is not None
    assert outcome.llm_version == "scripted/scripted-1"
    assert outcome.prompt_version == "cio_narrative@v1"
    assert llm.last_request is not None
    assert "BBCA" in llm.last_request.prompt
    assert "Dilarang" in llm.last_request.prompt  # rules travel with the prompt


async def test_narrator_rejects_fabricated_figures(container: Container) -> None:
    llm = ScriptedLLM("Kami perkirakan harga menyentuh 99.999 bulan depan.")
    outcome, _ = await _run_narrator(container, llm)
    assert outcome is None


async def test_narrator_survives_llm_failure(container: Container) -> None:
    outcome, _ = await _run_narrator(container, ScriptedLLM(None))
    assert outcome is None


async def test_service_embeds_narrative_and_persists_it(
    container: Container, tmp_path: Path
) -> None:
    from investment_os.core.service import AnalysisService
    from investment_os.data import Database, SqliteRecommendationStore

    db = Database(tmp_path / "narr.db")
    store = SqliteRecommendationStore(db)
    llm = ScriptedLLM("Sinyal teknikal dan fundamental sejalan; komite memilih BUY.")

    service = AnalysisService(
        container.kb,
        analysts=list(container.analysis._analysts),
        recommendation_store=store,
        narrator=Narrator(llm, PromptStore(PROMPTS_DIR)),
    )
    result = await service.analyze("BBCA")

    assert result.report.narrative is not None
    assert result.report.llm_version == "scripted/scripted-1"

    with db.transaction() as conn:
        row = conn.execute(
            "SELECT narrative, llm_version, prompt_version FROM recommendations LIMIT 1"
        ).fetchone()
    assert row["narrative"] == result.report.narrative
    assert row["llm_version"] == "scripted/scripted-1"
    assert row["prompt_version"] == "cio_narrative@v1"
    db.close()


@pytest.mark.parametrize("bad_env", [{}])
def test_container_llm_off_switch(container: Container, bad_env: dict[str, str]) -> None:
    # conftest builds the container with llm_provider="off"
    assert container.analysis._narrator is None
