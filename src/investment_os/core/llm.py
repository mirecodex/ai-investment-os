"""LLM port.

Core depends on this protocol only; concrete providers live in
``investment_os.llm``. The committee's decisions never depend on an LLM —
language models add narrative reasoning on top of rule-gated verdicts
(docs/fase-2: "LLM = reasoning, Decision Engine = guardrail").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    system: str
    prompt: str
    max_tokens: int = 700


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def version_tag(self) -> str:
        return f"{self.provider}/{self.model}"


class LLMClient(Protocol):
    provider: str
    model: str

    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    async def close(self) -> None: ...
