from __future__ import annotations

from typing import Any

import httpx

from investment_os.core.llm import LLMError, LLMRequest, LLMResponse
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)


class OpenAICompatClient:
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 60.0,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        # Auth goes per-request so an injected client (tests, custom pooling)
        # can never silently drop it.
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._http = http or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_s)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
        }
        try:
            response = await self._http.post(
                "/chat/completions", json=payload, headers=self._headers
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            raise LLMError(f"{self.provider}: {exc!r}") from exc

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{self.provider}: bentuk respons tidak dikenal") from exc

        usage = data.get("usage") or {}
        result = LLMResponse(
            text=text.strip(),
            provider=self.provider,
            model=str(data.get("model", self.model)),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
        )
        _record_usage(result)
        return result

    async def close(self) -> None:
        await self._http.aclose()


def _record_usage(response: LLMResponse) -> None:
    metrics.increment("llm_input_tokens", float(response.input_tokens), provider=response.provider)
    metrics.increment(
        "llm_output_tokens", float(response.output_tokens), provider=response.provider
    )
    log.info(
        "llm_call_completed",
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
