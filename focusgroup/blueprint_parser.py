"""The blueprint DSL.

A blueprint is a YAML map whose values may contain ``{{ function(args) }}``
templates. Each template is evaluated with plain Python randomness, so the
demographic mix of a persona pool is controlled by math, not by the LLM.

=====================  ==========================================  =======================
Function               Meaning                                     Example
=====================  ==========================================  =======================
``range(min, max)``    uniform integer, inclusive                  ``{{ range(25, 45) }}``
``choice(a, b, ...)``  uniform pick                                ``{{ choice(Cat, Dog) }}``
``weighted(k:w, ...)`` pick with weights (need not sum to 1)       ``{{ weighted(A:0.8, B:0.2) }}``
``normal(mean, std)``  integer from a bell curve                   ``{{ normal(75000, 15000) }}``
``bool(p)``            True with probability ``p``                 ``{{ bool(0.3) }}``
=====================  ==========================================  =======================
"""

from __future__ import annotations

import ast
import random
import re
from typing import Any

TEMPLATE = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.DOTALL)
CALL = re.compile(r"^(\w+)\((.*)\)$", re.DOTALL)


class BlueprintError(ValueError):
    """Raised for malformed templates."""


def split_args(args: str) -> list[str]:
    """Split on top-level commas, respecting quotes and parentheses."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    quote: str | None = None
    for ch in args:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def literal(token: str) -> Any:
    """Turn a token into a number/bool/string. Unquoted text stays a string."""
    token = token.strip()
    try:
        value = ast.literal_eval(token)
    except (ValueError, SyntaxError):
        return token
    # A bare `None` in a blueprint is a category label, not a null.
    return token if value is None else value


def split_pair(item: str) -> tuple[str, str]:
    """Split ``key:weight`` on the last colon that is outside quotes."""
    quote: str | None = None
    split_at = -1
    for i, ch in enumerate(item):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ":":
            split_at = i
    if split_at == -1:
        raise BlueprintError(f"weighted() expects key:weight pairs, got {item!r}")
    return item[:split_at], item[split_at + 1 :]


class BlueprintParser:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.functions = {
            "range": self._range,
            "choice": self._choice,
            "weighted": self._weighted,
            "normal": self._normal,
            "bool": self._bool,
        }

    def parse(self, text: str) -> Any:
        """Evaluate every template in ``text``.

        A value that is exactly one template returns the typed result (int, bool, str).
        Templates embedded in longer text are substituted as strings.
        """
        stripped = text.strip()
        whole = TEMPLATE.fullmatch(stripped)
        if whole:
            return self.evaluate(whole.group(1))
        return TEMPLATE.sub(lambda m: str(self.evaluate(m.group(1))), text)

    def evaluate(self, expression: str) -> Any:
        match = CALL.match(expression.strip())
        if not match:
            raise BlueprintError(f"Invalid template: {{{{ {expression} }}}}")
        name, args = match.groups()
        if name not in self.functions:
            known = ", ".join(self.functions)
            raise BlueprintError(f"Unknown function {name!r} (known: {known})")
        return self.functions[name](split_args(args))

    def _range(self, args: list[str]) -> int:
        low, high = (int(literal(a.split("=")[-1])) for a in args)
        return self.rng.randint(min(low, high), max(low, high))

    def _choice(self, args: list[str]) -> Any:
        if not args:
            raise BlueprintError("choice() needs at least one option")
        return self.rng.choice([literal(a) for a in args])

    def _weighted(self, args: list[str]) -> Any:
        options: list[Any] = []
        weights: list[float] = []
        for item in args:
            key, weight = split_pair(item)
            options.append(literal(key))
            weights.append(float(literal(weight)))
        if not options:
            raise BlueprintError("weighted() needs at least one key:weight pair")
        return self.rng.choices(options, weights=weights, k=1)[0]

    def _normal(self, args: list[str]) -> int:
        mean, std = (float(literal(a.split("=")[-1])) for a in args)
        return int(round(self.rng.gauss(mean, std)))

    def _bool(self, args: list[str]) -> bool:
        return self.rng.random() < float(literal(args[0]))

    def skeleton(self, blueprint: dict) -> dict:
        """Roll every template in a (possibly nested) blueprint."""
        result: dict = {}
        for key, value in blueprint.items():
            if isinstance(value, str):
                result[key] = self.parse(value)
            elif isinstance(value, dict):
                result[key] = self.skeleton(value)
            else:
                result[key] = value
        return result
