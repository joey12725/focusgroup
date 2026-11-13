"""The Analyst: turn a pile of transcripts into a decision.

Aggregation happens in two layers:

1. :func:`tally` counts what happened (interviews, errors, variants, models)
   with no LLM involved, so the numbers in the report header are exact.
2. :meth:`Analyst.report` hands every transcript to the report model with a
   fixed rubric: consensus (60%+ agreement), variance, outliers, and a
   Go / No-Go call. Split tests get a side-by-side rubric and a named winner.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .llm import LLM

SINGLE_RUBRIC = """\
You are a skeptical research analyst. You get transcripts of customer interviews
about one question. Synthesize them into a Markdown report with these sections:

## Consensus
What 60%+ of interviewees agree on. Give the rough share (e.g. "7 of 10").
## Variance
The real splits in the room and which kinds of people fall on each side.
## Outliers
Surprising answers worth a second look. Quote them briefly.
## Verdict
**Go**, **No-Go** or **Pivot**, with the two or three reasons that matter most
and the next question you would ask real customers.

Base every claim on the transcripts. Quote sparingly. No preamble.
"""

SPLIT_RUBRIC = """\
You are a skeptical research analyst reading an A/B test. Each group of interviews
saw a different variant of the same question. Write a Markdown report:

## Scoreboard
A table: variant, interviews, overall sentiment, purchase intent (low/med/high),
top objection.
## What Moved People
Why the stronger variant landed, with short quotes.
## What Backfired
Objections specific to each variant.
## Winner
Name the winning variant and how confident you are (low/medium/high), plus what
you would test next.

Base every claim on the transcripts. No preamble.
"""


def question_text(question: Any) -> str:
    if isinstance(question, list):
        return "\n".join(f"{i}. {q}" for i, q in enumerate(question, 1))
    return str(question)


def transcript(result: dict) -> str:
    who = result.get("persona_name") or result.get("persona", "persona")
    lines = [f"### {who}"]
    if "conversation" in result:
        for turn in result["conversation"]:
            role = "Interviewer" if turn["role"] == "interviewer" else "Persona"
            lines.append(f"{role}: {turn['content']}")
    elif "response" in result:  # sessions written by early versions
        lines.append(f"Persona: {result['response']}")
    return "\n".join(lines)


def tally(results: list[dict]) -> dict[str, Any]:
    ok = [r for r in results if r.get("status") == "success"]
    return {
        "interviews": len(results),
        "succeeded": len(ok),
        "failed": len(results) - len(ok),
        "variants": Counter(r["variant"] for r in ok if r.get("variant") is not None),
        "models": Counter(r.get("model", "unknown") for r in ok),
        "turns": sum(len(r.get("conversation", [])) for r in ok) // 2,
    }


def session_tests(session: dict) -> list[dict]:
    """Normalize single and batch sessions into a list of tests."""
    if session.get("type") == "batch" or "tests" in session:
        return session["tests"]
    return [
        {
            "question": session.get("question", session.get("initial_question")),
            "options": session.get("options"),
            "results": session.get("results", []),
        }
    ]


class Analyst:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def build_prompt(self, question: Any, results: list[dict]) -> tuple[str, str] | None:
        ok = [r for r in results if r.get("status") == "success"]
        if not ok:
            return None
        variants = [r.get("variant") for r in ok if r.get("variant") is not None]
        if variants:
            groups: dict[str, list[str]] = {}
            for r in ok:
                groups.setdefault(str(r.get("variant")), []).append(transcript(r))
            body = "\n\n".join(
                f"## Variant: {name} ({len(items)} interviews)\n\n" + "\n\n".join(items)
                for name, items in groups.items()
            )
            return SPLIT_RUBRIC, f"Question template:\n{question_text(question)}\n\n{body}"
        body = "\n\n".join(transcript(r) for r in ok)
        return SINGLE_RUBRIC, f"Question:\n{question_text(question)}\n\n{len(ok)} interviews:\n\n{body}"

    def analyze_test(self, question: Any, results: list[dict]) -> str:
        prompt = self.build_prompt(question, results)
        if prompt is None:
            return "_No successful interviews to analyze._"
        system, user = prompt
        return self.llm.complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=self.llm.report_model,
        )

    def report(self, session: dict) -> str:
        tests = session_tests(session)
        if len(tests) == 1:
            return self.analyze_test(tests[0]["question"], tests[0]["results"])
        sections = ["# Batch Report"]
        for i, test in enumerate(tests, 1):
            sections.append(f"## Test {i}: {question_text(test['question'])}")
            sections.append(self.analyze_test(test["question"], test["results"]))
        return "\n\n".join(sections)
