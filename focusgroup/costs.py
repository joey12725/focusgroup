"""Token and dollar accounting for a CLI run."""

from __future__ import annotations

import threading

# Fallback USD prices per 1M tokens (input, output), matched by substring of the
# model id. Only used when the provider does not report a cost itself
# (OpenRouter does, via ``usage.cost``).
FALLBACK_PRICING: dict[str, tuple[float, float]] = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "claude-haiku": (1.00, 5.00),
    "claude-sonnet": (3.00, 15.00),
    "deepseek": (0.27, 1.10),
    "grok": (0.20, 0.50),
    "kimi": (0.60, 2.50),
}
DEFAULT_PRICE = (1.00, 3.00)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    model_lower = model.lower()
    input_rate, output_rate = DEFAULT_PRICE
    for key, rates in FALLBACK_PRICING.items():
        if key in model_lower:
            input_rate, output_rate = rates
            break
    return input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate


class CostTracker:
    """Thread-safe running total of tokens and spend."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = 0.0

    def add(self, model: str, input_tokens: int, output_tokens: int, reported_cost: float | None = None) -> None:
        cost = reported_cost if reported_cost is not None else estimate_cost(model, input_tokens, output_tokens)
        with self._lock:
            self.calls += 1
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_cost += cost

    def summary(self) -> str:
        return (
            f"{self.calls} LLM calls · {self.input_tokens:,} tokens in · "
            f"{self.output_tokens:,} tokens out · ${self.total_cost:.4f}"
        )
