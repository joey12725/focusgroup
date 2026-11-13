from focusgroup.mom_test import SYSTEM_PROMPT, MomTest

from .conftest import FakeLLM


def test_rewrites_and_strips_quotes():
    llm = FakeLLM('"When did a plant of yours last die?"')
    assert MomTest(llm).rewrite("Would you buy a plant sensor?") == "When did a plant of yours last die?"
    assert llm.calls[0][1][0]["content"] == SYSTEM_PROMPT


def test_agent_slots_and_lists():
    llm = FakeLLM("rewritten")
    out = MomTest(llm).rewrite_all(["Would you pay ***?", "AGENT(dig into price)"])
    assert out == ["rewritten", "AGENT(dig into price)"]
    assert len(llm.calls) == 1
