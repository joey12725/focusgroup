"""Rewrite leading questions into Mom Test questions.

Based on Rob Fitzpatrick's *The Mom Test*: ask about the past and specifics,
never about hypothetical futures or your idea.
"""

from __future__ import annotations

from .llm import LLM

SYSTEM_PROMPT = """\
You are an expert in "The Mom Test" by Rob Fitzpatrick. Rewrite bad customer
discovery questions (future tense, hypothetical, fishing for compliments) into
good ones (past tense, specific, about facts and behavior).

Rules:
1. No "Would you..." questions.
2. No pitching.
3. Ask about specific past behavior and problems.
4. Keep it conversational and brief.
5. Keep any *** placeholder exactly as written.
6. If the question is already good, return it unchanged.

Reply with the rewritten question only.

Bad: "Would you pay for an app that tracks your sleep?"
Good: "How do you keep track of your sleep today? Have you ever paid for something to help?"
"""


class MomTest:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def rewrite(self, question: str) -> str:
        if question.strip().startswith(("ASSISTANT(", "AGENT(")):
            return question
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        return self.llm.complete(messages).strip().strip('"')

    def rewrite_all(self, question: str | list[str]) -> str | list[str]:
        if isinstance(question, list):
            return [self.rewrite(q) for q in question]
        return self.rewrite(question)
