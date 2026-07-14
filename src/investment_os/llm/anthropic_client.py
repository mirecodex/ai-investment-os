from __future__ import annotations

from typing import Any

from investment_os.core.llm import LLMError, LLMRequest, LLMResponse
from investment_os.llm.openai_compat import _record_usage


class AnthropicClient:
    provider = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-opus-4-8",
        client: Any | None = None,
    ) -> None:
        self.model = model
        if client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - depends on extras
                raise LLMError(
                    "paket 'anthropic' belum terpasang — install dengan "
                    "pip install 'investment-os[anthropic]'"
                ) from exc
            client = anthropic.AsyncAnthropic(api_key=api_key)
        self._client = client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.prompt}],
            )
        except Exception as exc:  # SDK raises its own typed hierarchy
            raise LLMError(f"anthropic: {exc!r}") from exc

        if getattr(message, "stop_reason", None) == "refusal":
            raise LLMError("anthropic: permintaan ditolak oleh safety classifier")

        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        usage = getattr(message, "usage", None)
        result = LLMResponse(
            text=text.strip(),
            provider=self.provider,
            model=str(getattr(message, "model", self.model)),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )
        _record_usage(result)
        return result

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            await close()
