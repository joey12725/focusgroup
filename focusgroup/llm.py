"""A small wrapper around any OpenAI-compatible chat completions endpoint.

Every component (architect, persona writer, interviewer, analyst) talks to the
model through :class:`LLM`, so swapping providers, mocking in tests or adding a
new backend only touches this file.
"""

from __future__ import annotations

from typing import Any

from .config import Settings
from .costs import CostTracker

Message = dict[str, str]


class LLMError(RuntimeError):
    """Raised when the provider returns nothing usable."""


class LLM:
    def __init__(self, settings: Settings, client: Any = None, async_client: Any = None) -> None:
        self.settings = settings
        self.costs = CostTracker()
        self._client = client
        self._async_client = async_client

    @property
    def models(self) -> list[str]:
        return self.settings.models

    @property
    def default_model(self) -> str:
        return self.settings.default_model

    @property
    def report_model(self) -> str:
        return self.settings.report_model

    # Clients are created lazily so `--help` and offline commands never need a key.
    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(base_url=self.settings.base_url, api_key=self._require_key())
        return self._client

    @property
    def async_client(self) -> Any:
        if self._async_client is None:
            from openai import AsyncOpenAI

            self._async_client = AsyncOpenAI(base_url=self.settings.base_url, api_key=self._require_key())
        return self._async_client

    def _require_key(self) -> str:
        if not self.settings.api_key:
            raise LLMError(
                "No API key found. Set FOCUSGROUP_API_KEY (or OPENROUTER_API_KEY / OPENAI_API_KEY), "
                "or put it in a .env file."
            )
        return self.settings.api_key

    def complete(self, messages: list[Message], model: str | None = None) -> str:
        model = model or self.default_model
        response = self.client.chat.completions.create(model=model, messages=messages)
        return self._unpack(response, model)

    async def acomplete(self, messages: list[Message], model: str | None = None) -> str:
        model = model or self.default_model
        response = await self.async_client.chat.completions.create(model=model, messages=messages)
        return self._unpack(response, model)

    def _unpack(self, response: Any, model: str) -> str:
        usage = getattr(response, "usage", None)
        if usage is not None:
            reported = getattr(usage, "cost", None)
            self.costs.add(
                model,
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
                reported if isinstance(reported, (int, float)) else None,
            )
        choices = getattr(response, "choices", None) or []
        content = choices[0].message.content if choices else None
        if not content or not content.strip():
            raise LLMError(f"{model} returned an empty response")
        return content.strip()
