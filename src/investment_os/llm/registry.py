from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from investment_os.core.llm import LLMClient, LLMError
from investment_os.llm.anthropic_client import AnthropicClient
from investment_os.llm.openai_compat import OpenAICompatClient
from investment_os.observability import get_logger

log = get_logger(__name__)

_ANTHROPIC = "anthropic-messages"
_OPENAI_COMPAT = "openai-compat"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    env_key: str
    kind: str
    base_url: str
    default_model: str


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("anthropic", "ANTHROPIC_API_KEY", _ANTHROPIC, "", "claude-opus-4-8"),
    ProviderSpec("openai", "OPENAI_API_KEY", _OPENAI_COMPAT, "https://api.openai.com/v1", "gpt-4o"),
    ProviderSpec(
        "google",
        "GOOGLE_API_KEY",
        _OPENAI_COMPAT,
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.5-flash",
    ),
    ProviderSpec("xai", "XAI_API_KEY", _OPENAI_COMPAT, "https://api.x.ai/v1", "grok-4"),
    ProviderSpec(
        "deepseek",
        "DEEPSEEK_API_KEY",
        _OPENAI_COMPAT,
        "https://api.deepseek.com/v1",
        "deepseek-chat",
    ),
    ProviderSpec(
        "qwen",
        "DASHSCOPE_API_KEY",
        _OPENAI_COMPAT,
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
    ProviderSpec(
        "qwen-cn",
        "DASHSCOPE_CN_API_KEY",
        _OPENAI_COMPAT,
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
    ProviderSpec("glm", "ZHIPU_API_KEY", _OPENAI_COMPAT, "https://api.z.ai/api/paas/v4", "glm-4.6"),
    ProviderSpec(
        "glm-cn",
        "ZHIPU_CN_API_KEY",
        _OPENAI_COMPAT,
        "https://open.bigmodel.cn/api/paas/v4",
        "glm-4.6",
    ),
    ProviderSpec(
        "minimax", "MINIMAX_API_KEY", _OPENAI_COMPAT, "https://api.minimax.io/v1", "MiniMax-M1"
    ),
    ProviderSpec(
        "minimax-cn",
        "MINIMAX_CN_API_KEY",
        _OPENAI_COMPAT,
        "https://api.minimaxi.com/v1",
        "MiniMax-M1",
    ),
    ProviderSpec(
        "openrouter",
        "OPENROUTER_API_KEY",
        _OPENAI_COMPAT,
        "https://openrouter.ai/api/v1",
        "openrouter/auto",
    ),
)

_BY_NAME = {spec.name: spec for spec in PROVIDERS}


def available_providers(env: Mapping[str, str] | None = None) -> list[str]:
    env = env if env is not None else os.environ
    return [spec.name for spec in PROVIDERS if env.get(spec.env_key)]


def resolve_llm(
    provider: str | None = None,
    model: str | None = None,
    env: Mapping[str, str] | None = None,
) -> LLMClient | None:
    env = env if env is not None else os.environ

    if provider:
        spec = _BY_NAME.get(provider)
        if spec is None:
            raise LLMError(
                f"provider LLM tidak dikenal: '{provider}' (pilihan: {', '.join(sorted(_BY_NAME))})"
            )
        api_key = env.get(spec.env_key)
        if not api_key:
            raise LLMError(f"provider '{provider}' dipilih tetapi {spec.env_key} tidak diset")
        return _build(spec, api_key, model)

    for spec in PROVIDERS:
        api_key = env.get(spec.env_key)
        if api_key:
            log.info("llm_provider_selected", provider=spec.name)
            return _build(spec, api_key, model)
    return None


def _build(spec: ProviderSpec, api_key: str, model: str | None) -> LLMClient:
    chosen_model = model or spec.default_model
    if spec.kind == _ANTHROPIC:
        return AnthropicClient(api_key=api_key, model=chosen_model)
    return OpenAICompatClient(
        provider=spec.name,
        base_url=spec.base_url,
        api_key=api_key,
        model=chosen_model,
    )
