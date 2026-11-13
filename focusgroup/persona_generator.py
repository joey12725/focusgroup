"""Persona generation: roll a skeleton with math, then let the LLM write the person."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Callable

from .blueprint_parser import BlueprintParser
from .llm import LLM
from .project import Project

SYSTEM_PROMPT = """\
You are a novelist casting a focus group. You get a skeleton of raw attributes for
one person. Breathe life into them and connect the dots: if they are "Angry" and
"Broke", invent the reason. Keep every attribute exactly as given.

Return Markdown:
1. YAML front matter (between --- lines) containing every skeleton attribute,
   plus `name` (invent one) and `skepticism` (0-100, from their personality).
2. A one-line quote in their voice.
3. Short sections: "The Context", "How They Buy", "What Would Make Them Walk".
Keep it under 350 words.
"""


class PersonaGenerator:
    def __init__(self, project: Project, llm: LLM, seed: int | None = None) -> None:
        self.project = project
        self.llm = llm
        self.parser = BlueprintParser(random.Random(seed))

    def skeleton(self, blueprint: dict) -> dict:
        return self.parser.skeleton(blueprint)

    async def write_persona(self, skeleton: dict) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Skeleton:\n{json.dumps(skeleton, indent=2)}"},
        ]
        return await self.llm.acomplete(messages)

    async def generate(self, count: int, on_done: Callable[[int], None] | None = None) -> list[str]:
        """Generate ``count`` personas in parallel and save them.

        Skeletons are rolled up front, in order, so ``--seed`` makes the
        demographic mix reproducible even though the LLM calls finish out of order.
        Numbering continues after any personas already in the project.
        """
        blueprint = self.project.load_blueprint()
        start = self.project.next_persona_index()
        skeletons = [self.skeleton(blueprint) for _ in range(count)]
        semaphore = asyncio.Semaphore(self.llm.settings.concurrency)

        async def one(index: int, skeleton: dict) -> str:
            async with semaphore:
                content = await self.write_persona(skeleton)
            path = self.project.save_persona(index, content)
            if on_done:
                on_done(index)
            return path.name

        return await asyncio.gather(*(one(start + i, s) for i, s in enumerate(skeletons)))
