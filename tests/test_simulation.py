import asyncio
import random

from focusgroup.project import Project
from focusgroup.simulation import Simulation, apply_variant, front_matter, persona_label

from .conftest import FakeLLM, system_text

PERSONA = {"filename": "p_001.md", "content": "---\nname: Dana Ruiz\nAge: 34\n---\nLoves ferns."}


def run(coro):
    return asyncio.run(coro)


def test_single_question_interview():
    llm = FakeLLM("Honestly? I'd forget to charge it.")
    result = run(Simulation(llm).interview(PERSONA, "Would you buy this?"))
    assert result["status"] == "success"
    assert result["persona_name"] == "Dana Ruiz (p_001)"
    assert [t["role"] for t in result["conversation"]] == ["interviewer", "persona"]
    # The persona sees its own profile in the system prompt.
    assert "Loves ferns." in system_text(llm.calls[0][1])


def test_scripted_sequence_then_followups():
    def reply(messages, model):
        return "FOLLOWUP?" if "follow-up" in system_text(messages) else "answer"

    llm = FakeLLM(reply)
    result = run(Simulation(llm).interview(PERSONA, ["Q1", "Q2"], depth=1))
    said = [t["content"] for t in result["conversation"] if t["role"] == "interviewer"]
    assert said == ["Q1", "Q2", "FOLLOWUP?"]
    assert len(result["conversation"]) == 6


def test_agent_tag_is_replaced_by_moderator_message():
    def reply(messages, model):
        return "Generated question" if "moderating" in system_text(messages) else "answer"

    llm = FakeLLM(reply)
    result = run(Simulation(llm).interview(PERSONA, ["Q1", "AGENT(ask about price)"]))
    said = [t["content"] for t in result["conversation"] if t["role"] == "interviewer"]
    assert said == ["Q1", "Generated question"]
    assert "ask about price" in system_text(llm.calls[1][1])


def test_persona_sees_interviewer_as_user():
    llm = FakeLLM("a")
    run(Simulation(llm).interview(PERSONA, ["Q1", "Q2"]))
    last_messages = llm.calls[-1][1]
    chat = [m for m in last_messages if m["role"] != "system"]
    assert [m["role"] for m in chat] == ["user", "assistant", "user"]


def test_error_marks_interview_failed_without_raising():
    llm = FakeLLM(lambda m, model: RuntimeError("rate limited"))
    result = run(Simulation(llm).interview(PERSONA, "Q"))
    assert result["status"] == "error"
    assert "rate limited" in result["error"]


def test_split_test_deals_variants_round_robin():
    llm = FakeLLM(lambda m, model: m[-1]["content"])  # echo the question back
    personas = [dict(PERSONA, filename=f"p_{i}.md") for i in range(4)]
    results = run(Simulation(llm, random.Random(0)).run(personas, "Pay ***?", options=["$6", "$12"]))
    assert [r["variant"] for r in results] == ["$6", "$12", "$6", "$12"]
    assert [r["conversation"][1]["content"] for r in results] == ["Pay $6?", "Pay $12?", "Pay $6?", "Pay $12?"]


def test_models_are_drawn_from_pool():
    llm = FakeLLM("a", models=["m/one", "m/two"])
    personas = [dict(PERSONA, filename=f"p_{i}.md") for i in range(20)]
    results = run(Simulation(llm, random.Random(1)).run(personas, "Q"))
    assert {r["model"] for r in results} == {"m/one", "m/two"}


def test_apply_variant_on_lists():
    assert apply_variant(["a ***", "b"], "X") == ["a X", "b"]


def test_front_matter_handles_missing_or_broken_yaml():
    assert front_matter("no front matter") == {}
    assert front_matter("---\n: : :\n---\n") == {}
    assert persona_label({"filename": "p_9.md", "content": "plain"}) == "p_9"


def test_sampling_from_example_project(example_project):
    project = Project(example_project)
    picked = project.sample_personas(3, random.Random(0))
    assert len(picked) == 3
    assert len({p["filename"] for p in picked}) == 3
    assert project.sample_personas(999) and len(project.sample_personas(999)) == len(project.persona_files())
