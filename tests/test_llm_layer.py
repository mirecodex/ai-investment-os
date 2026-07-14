from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from investment_os.core.llm import LLMError, LLMRequest
from investment_os.llm.anthropic_client import AnthropicClient
from investment_os.llm.openai_compat import OpenAICompatClient
from investment_os.llm.promptstore import PromptNotFoundError, PromptStore
from investment_os.llm.registry import resolve_llm

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


# -- provider registry --------------------------------------------------------


def test_no_keys_means_no_llm() -> None:
    assert resolve_llm(env={}) is None


def test_first_configured_provider_wins() -> None:
    env = {"DEEPSEEK_API_KEY": "k1", "OPENROUTER_API_KEY": "k2"}
    client = resolve_llm(env=env)
    assert client is not None
    assert client.provider == "deepseek"
    assert client.model == "deepseek-chat"


def test_explicit_provider_and_model_override() -> None:
    env = {"OPENAI_API_KEY": "k1", "XAI_API_KEY": "k2"}
    client = resolve_llm("xai", "grok-3-mini", env=env)
    assert client is not None
    assert client.provider == "xai"
    assert client.model == "grok-3-mini"


def test_explicit_provider_without_key_errors() -> None:
    with pytest.raises(LLMError, match="GOOGLE_API_KEY"):
        resolve_llm("google", env={})


def test_unknown_provider_errors() -> None:
    with pytest.raises(LLMError, match="tidak dikenal"):
        resolve_llm("skynet", env={"OPENAI_API_KEY": "k"})


# -- OpenAI-compatible adapter -------------------------------------------------


async def test_openai_compat_request_and_response_mapping() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "test-model-v2",
                "choices": [{"message": {"content": "  Halo dunia.  "}}],
                "usage": {"prompt_tokens": 42, "completion_tokens": 7},
            },
        )

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://llm.example/v1"
    )
    client = OpenAICompatClient(
        provider="testprov",
        base_url="https://llm.example/v1",
        api_key="sk-test",
        model="test-model",
        http=http,
    )
    response = await client.complete(LLMRequest(system="sistem", prompt="pertanyaan"))

    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "test-model"
    assert body["messages"][0] == {"role": "system", "content": "sistem"}

    assert response.text == "Halo dunia."
    assert response.model == "test-model-v2"
    assert response.input_tokens == 42
    assert response.output_tokens == 7
    await client.close()


async def test_openai_compat_http_error_becomes_llm_error() -> None:
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(429, json={})),
        base_url="https://llm.example/v1",
    )
    client = OpenAICompatClient(
        provider="testprov",
        base_url="https://llm.example/v1",
        api_key="sk",
        model="m",
        http=http,
    )
    with pytest.raises(LLMError):
        await client.complete(LLMRequest(system="s", prompt="p"))
    await client.close()


# -- Anthropic adapter (SDK client injected as a fake) --------------------------


class _Block:
    def __init__(self, type_: str, text: str) -> None:
        self.type = type_
        self.text = text


class _Usage:
    input_tokens = 100
    output_tokens = 25


class _Message:
    def __init__(self) -> None:
        self.model = "claude-opus-4-8"
        self.stop_reason = "end_turn"
        self.usage = _Usage()
        self.content = [_Block("thinking", "..."), _Block("text", "Narasi CIO.")]


class _FakeMessages:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> _Message:
        self.kwargs = kwargs
        return _Message()


class _FakeAnthropic:
    def __init__(self) -> None:
        self.messages = _FakeMessages()

    async def close(self) -> None:
        pass


async def test_anthropic_adapter_maps_messages_api() -> None:
    fake = _FakeAnthropic()
    client = AnthropicClient(api_key="sk-ant", client=fake)
    response = await client.complete(LLMRequest(system="sistem", prompt="pertanyaan"))

    assert fake.messages.kwargs["model"] == "claude-opus-4-8"
    assert fake.messages.kwargs["system"] == "sistem"
    assert fake.messages.kwargs["messages"] == [{"role": "user", "content": "pertanyaan"}]

    assert response.text == "Narasi CIO."  # thinking block excluded
    assert response.input_tokens == 100
    await client.close()


async def test_anthropic_refusal_becomes_llm_error() -> None:
    fake = _FakeAnthropic()

    async def refuse(**kwargs: object) -> _Message:
        message = _Message()
        message.stop_reason = "refusal"
        return message

    fake.messages.create = refuse  # type: ignore[method-assign]
    client = AnthropicClient(api_key="sk-ant", client=fake)
    with pytest.raises(LLMError, match="ditolak"):
        await client.complete(LLMRequest(system="s", prompt="p"))


# -- prompt store ----------------------------------------------------------------


def test_prompt_store_loads_versioned_template() -> None:
    store = PromptStore(PROMPTS_DIR)
    template = store.get("cio_narrative")
    assert template.tag == "cio_narrative@v1"
    assert "{ticker}" in template.text


def test_prompt_store_missing_prompt_raises() -> None:
    store = PromptStore(PROMPTS_DIR)
    with pytest.raises(PromptNotFoundError):
        store.get("does_not_exist")
