import json

from focusgroup.analyst import SINGLE_RUBRIC, SPLIT_RUBRIC, Analyst, session_tests, tally

from .conftest import EXAMPLE, FakeLLM


def ok(persona, answer, variant=None, model="m/a"):
    return {
        "persona": persona,
        "persona_name": persona,
        "model": model,
        "variant": variant,
        "status": "success",
        "conversation": [{"role": "interviewer", "content": "Q"}, {"role": "persona", "content": answer}],
    }


def test_tally_counts_without_llm():
    results = [ok("a", "x", "$6"), ok("b", "y", "$12", "m/b"), {"persona": "c", "status": "error"}]
    t = tally(results)
    assert (t["interviews"], t["succeeded"], t["failed"], t["turns"]) == (3, 2, 1, 2)
    assert t["variants"] == {"$6": 1, "$12": 1}
    assert t["models"] == {"m/a": 1, "m/b": 1}


def test_single_question_uses_consensus_rubric():
    llm = FakeLLM("## Verdict\n**Go**")
    llm.settings.analyst_model = "big/model"
    report = Analyst(llm).report({"question": "Q", "results": [ok("a", "I love it"), ok("b", "meh")]})
    model, messages = llm.calls[0]
    assert report.startswith("## Verdict")
    assert model == "big/model"
    assert messages[0]["content"] == SINGLE_RUBRIC
    assert "I love it" in messages[1]["content"] and "2 interviews" in messages[1]["content"]


def test_split_test_groups_by_variant():
    llm = FakeLLM("report")
    Analyst(llm).report({"question": "Pay ***?", "results": [ok("a", "cheap!", "$6"), ok("b", "pricey", "$12")]})
    system, user = (m["content"] for m in llm.calls[0][1])
    assert system == SPLIT_RUBRIC
    assert "## Variant: $6 (1 interviews)" in user and "## Variant: $12 (1 interviews)" in user


def test_no_successes_skips_llm():
    llm = FakeLLM("never")
    assert "No successful" in Analyst(llm).report({"question": "Q", "results": [{"status": "error"}]})
    assert llm.calls == []


def test_batch_session_reports_each_test():
    llm = FakeLLM("section")
    session = {
        "type": "batch",
        "tests": [{"question": "A", "results": [ok("a", "x")]}, {"question": "B", "results": [ok("b", "y")]}],
    }
    report = Analyst(llm).report(session)
    assert len(llm.calls) == 2
    assert "## Test 1: A" in report and "## Test 2: B" in report


def test_legacy_session_format_is_understood():
    legacy = {"initial_question": "Q", "results": [{"status": "success", "persona": "p1.md", "response": "old"}]}
    llm = FakeLLM("r")
    Analyst(llm).report(legacy)
    assert "Persona: old" in llm.calls[0][1][1]["content"]
    assert session_tests(legacy)[0]["question"] == "Q"


def test_example_session_round_trips():
    session = json.loads(next((EXAMPLE / "sessions").glob("*.json")).read_text())
    t = tally(session_tests(session)[0]["results"])
    assert t["succeeded"] == t["interviews"] > 0
