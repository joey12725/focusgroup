"""The Architect turns a product brief into a blueprint.yaml."""

from __future__ import annotations

import yaml

from .blueprint_parser import BlueprintParser
from .llm import LLM

SYSTEM_PROMPT = """\
You are The Architect. Translate a product description into a strict statistical
configuration (the Blueprint) for generating the people who might buy it.

Output a valid YAML mapping and nothing else. Every value is a quoted template that
uses exactly one of these functions, wrapped in double curly braces:

- "{{ range(min, max) }}"            uniform integer
- "{{ choice(A, B, C) }}"            uniform pick
- "{{ weighted(A:0.6, B:0.3, C:0.1) }}"  weighted pick
- "{{ normal(mean, std) }}"          bell-curve integer
- "{{ bool(0.3) }}"                  true with that probability

Example:
Age: "{{ normal(38, 9) }}"
Role: "{{ choice(Founder, Ops_Lead, Freelancer) }}"
Budget_Sensitivity: "{{ weighted(Price_Shopper:0.3, Value_Buyer:0.5, Premium:0.2) }}"

Rules:
- Flat key/value map. No nesting, no lists, no comments, no markdown fences.
- Include standard demographics (age, income, role, location).
- Include 3-5 psychographic variables that would change a buying decision for THIS
  product (risk tolerance, current workaround, skepticism, taste, ...).
- Include one or two "life randomizers" (current mood, a recent event) so the
  people feel lived-in.
"""


def strip_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3]
    return text.strip()


def validate_blueprint(content: str) -> dict:
    """Parse the YAML and roll it once, so a broken blueprint fails at `init`, not later."""
    data = yaml.safe_load(content)
    if not isinstance(data, dict) or not data:
        raise ValueError("Blueprint must be a non-empty YAML mapping")
    BlueprintParser().skeleton(data)
    return data


class Architect:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def create_blueprint(self, project_name: str, brief: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Project: {project_name}\n\nProduct brief:\n{brief}\n\nWrite blueprint.yaml."},
        ]
        content = strip_fences(self.llm.complete(messages))
        try:
            validate_blueprint(content)
        except Exception as first_error:  # one repair attempt, then surface the error
            messages += [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": f"That blueprint failed to parse ({first_error}). Return a corrected version.",
                },
            ]
            content = strip_fences(self.llm.complete(messages))
            validate_blueprint(content)
        return content
