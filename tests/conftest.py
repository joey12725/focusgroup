"""Shared fixtures. No test ever talks to a real model."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from focusgroup.config import Settings
from focusgroup.llm import LLM

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "fernando"


class FakeLLM(LLM):
    """An LLM whose replies come from a Python function instead of a network call."""

    def __init__(self, reply: Callable[[list[dict], str], str] | str = "ok", models: list[str] | None = None):
        super().__init__(Settings(api_key="test", models=models or ["fake/model-a"], concurrency=4))
        self.reply = reply
        self.calls: list[tuple[str, list[dict]]] = []

    def _answer(self, messages: list[dict], model: str | None) -> str:
        model = model or self.default_model
        self.calls.append((model, messages))
        self.costs.add(model, 100, 20)
        text = self.reply(messages, model) if callable(self.reply) else self.reply
        if isinstance(text, Exception):
            raise text
        return text

    def complete(self, messages, model=None):
        return self._answer(messages, model)

    async def acomplete(self, messages, model=None):
        return self._answer(messages, model)


def system_text(messages: list[dict]) -> str:
    return "\n".join(m["content"] for m in messages if m["role"] == "system")


@pytest.fixture
def fake_llm():
    return FakeLLM


@pytest.fixture
def example_project(tmp_path):
    """A writable copy of the bundled example project."""
    import shutil

    dest = tmp_path / "projects" / "fernando"
    shutil.copytree(EXAMPLE, dest)
    return dest
