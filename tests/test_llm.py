import asyncio
from types import SimpleNamespace

import pytest

from focusgroup.config import Settings
from focusgroup.costs import CostTracker, estimate_cost
from focusgroup.llm import LLM, LLMError


def response(text, cost=None):
    usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=500, cost=cost)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=usage)


class StubCompletions:
    def __init__(self, resp):
        self.resp = resp
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.resp


class AsyncStubCompletions(StubCompletions):
    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self.resp


def client(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_complete_uses_default_model_and_tracks_reported_cost():
    comp = StubCompletions(response("  hi  ", cost=0.002))
    llm = LLM(Settings(api_key="k", models=["a/b"]), client=client(comp))
    assert llm.complete([{"role": "user", "content": "x"}]) == "hi"
    assert comp.kwargs["model"] == "a/b"
    assert llm.costs.total_cost == pytest.approx(0.002)
    assert llm.costs.input_tokens == 1000


def test_async_complete_estimates_cost_when_not_reported():
    comp = AsyncStubCompletions(response("yo"))
    llm = LLM(Settings(api_key="k"), async_client=client(comp))
    assert asyncio.run(llm.acomplete([], model="openai/gpt-5-mini")) == "yo"
    assert llm.costs.total_cost == pytest.approx(estimate_cost("openai/gpt-5-mini", 1000, 500))


def test_empty_response_raises():
    llm = LLM(Settings(api_key="k"), client=client(StubCompletions(response("   "))))
    with pytest.raises(LLMError):
        llm.complete([])


def test_missing_key_has_helpful_error():
    with pytest.raises(LLMError, match="FOCUSGROUP_API_KEY"):
        LLM(Settings(api_key=None)).complete([])


def test_cost_summary_format():
    t = CostTracker()
    t.add("x", 1200, 300, 0.01)
    assert t.summary() == "1 LLM calls · 1,200 tokens in · 300 tokens out · $0.0100"
