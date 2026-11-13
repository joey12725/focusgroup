"""The interview room: sample personas, ask questions, record transcripts."""

from __future__ import annotations

import asyncio
import random
import re
from typing import Any

import yaml

from .llm import LLM

PLACEHOLDER = "***"
AGENT_TAG = re.compile(r"^(?:ASSISTANT|AGENT)\((.*)\)$", re.DOTALL)

PERSONA_PROMPT = """\
You are a roleplay actor. Below is the profile of the person you are playing.
Become them completely. Answer the interviewer the way this person actually would,
given their mood, money, habits and skepticism. Be honest, including when the
honest answer is "no". Keep it brief and conversational. Never break character
and never mention being an AI.
"""

FOLLOWUP_PROMPT = """\
You are a sharp customer-discovery interviewer. Read the conversation and ask ONE
short follow-up that digs into the interviewee's last answer: the why, a concrete
past example, or what they actually do today. No pitching, no repeats.
Reply with the question only.
"""

AGENT_PROMPT = """\
You are moderating a customer interview. Write the interviewer's next message by
following this instruction, using the conversation so far as context.
Reply with the message only.

Instruction: {instruction}
"""

Question = str | list[str]


def front_matter(content: str) -> dict:
    """Return the YAML front matter of a persona file, or {} if there is none."""
    match = re.match(r"^\s*---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def persona_label(persona: dict[str, str]) -> str:
    meta = front_matter(persona["content"])
    name = meta.get("name") or meta.get("Name")
    stem = persona["filename"].removesuffix(".md")
    return f"{name} ({stem})" if name else stem


def as_chat(conversation: list[dict], interviewer_role: str = "user") -> list[dict[str, str]]:
    """Map transcript roles onto chat roles from the point of view of one speaker."""
    other = "assistant" if interviewer_role == "user" else "user"
    return [
        {"role": interviewer_role if turn["role"] == "interviewer" else other, "content": turn["content"]}
        for turn in conversation
    ]


def apply_variant(question: Question, variant: str) -> Question:
    if isinstance(question, list):
        return [q.replace(PLACEHOLDER, variant) for q in question]
    return question.replace(PLACEHOLDER, variant)


def has_placeholder(question: Question) -> bool:
    questions = question if isinstance(question, list) else [question]
    return any(PLACEHOLDER in q for q in questions)


class Simulation:
    def __init__(self, llm: LLM, rng: random.Random | None = None) -> None:
        self.llm = llm
        self.rng = rng or random.Random()

    async def followup(self, conversation: list[dict], model: str) -> str:
        messages = [{"role": "system", "content": FOLLOWUP_PROMPT}, *as_chat(conversation, "assistant")]
        try:
            return await self.llm.acomplete(messages, model=model)
        except Exception:
            return "Can you walk me through the last time that happened?"

    async def agent_message(self, conversation: list[dict], instruction: str, model: str) -> str:
        messages = [
            {"role": "system", "content": AGENT_PROMPT.format(instruction=instruction)},
            *as_chat(conversation, "assistant"),
        ]
        if len(messages) == 1:
            messages.append({"role": "user", "content": "Begin the interview."})
        try:
            return await self.llm.acomplete(messages, model=model)
        except Exception:
            return instruction

    async def interview(
        self,
        persona: dict[str, str],
        question: Question,
        depth: int = 0,
        variant: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Run one interview: scripted question(s) first, then ``depth`` follow-ups."""
        model = model or self.llm.default_model
        queue: list[str | None] = list(question) if isinstance(question, list) else [question]
        queue += [None] * depth  # None = let the interviewer improvise

        conversation: list[dict] = []
        result: dict[str, Any] = {
            "persona": persona["filename"],
            "persona_name": persona_label(persona),
            "model": model,
            "variant": variant,
            "status": "success",
            "conversation": conversation,
        }
        for scripted in queue:
            if scripted is None:
                text = await self.followup(conversation, model)
            elif match := AGENT_TAG.match(scripted.strip()):
                text = await self.agent_message(conversation, match.group(1).strip(), model)
            else:
                text = scripted
            conversation.append({"role": "interviewer", "content": text.strip() or "Could you say more?"})

            messages = [
                {"role": "system", "content": PERSONA_PROMPT},
                {"role": "system", "content": f"Persona profile:\n{persona['content']}"},
                *as_chat(conversation, "user"),
            ]
            try:
                answer = await self.llm.acomplete(messages, model=model)
            except Exception as exc:  # keep the rest of the panel going
                result["status"] = "error"
                result["error"] = f"{type(exc).__name__}: {exc}"
                break
            conversation.append({"role": "persona", "content": answer})
        return result

    async def run(
        self,
        personas: list[dict[str, str]],
        question: Question,
        depth: int = 0,
        options: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Interview every persona concurrently.

        With ``options`` this is a split test: personas (already randomly sampled)
        are dealt round-robin across variants and ``***`` in the question is
        replaced by that persona's variant. Each interview draws its model at
        random from the configured pool, so no single model's quirks dominate.
        """
        semaphore = asyncio.Semaphore(self.llm.settings.concurrency)

        async def one(index: int, persona: dict[str, str]) -> dict[str, Any]:
            variant = options[index % len(options)] if options else None
            q = apply_variant(question, variant) if variant is not None else question
            model = self.rng.choice(self.llm.models)
            async with semaphore:
                return await self.interview(persona, q, depth, variant, model)

        return list(await asyncio.gather(*(one(i, p) for i, p in enumerate(personas))))
