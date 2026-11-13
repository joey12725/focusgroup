# Extending focusgroup

The codebase is small and each stage is one module, so most extensions touch one file.

| Want to... | Edit |
|---|---|
| Add a DSL function (say, `lognormal`) | `blueprint_parser.py`: write a `_lognormal(self, args)` method and register it in `self.functions` |
| Change how personas are written | `persona_generator.py`: `SYSTEM_PROMPT` |
| Change how personas behave in interviews | `simulation.py`: `PERSONA_PROMPT` |
| Change the follow-up interviewer | `simulation.py`: `FOLLOWUP_PROMPT` |
| Change the report format | `analyst.py`: `SINGLE_RUBRIC` / `SPLIT_RUBRIC` |
| Use a non-OpenAI-compatible provider | `llm.py`: subclass `LLM` and override `complete` / `acomplete` |
| Add a command | `cli.py`: add a `@app.command()` and get a model with `get_llm()` |

## Custom model backends

Everything goes through two methods:

```python
class LLM:
    def complete(self, messages: list[dict], model: str | None = None) -> str: ...
    async def acomplete(self, messages: list[dict], model: str | None = None) -> str: ...
```

Subclass `LLM`, override both, and point the CLI at it:

```python
from focusgroup import cli
from focusgroup.llm import LLM


class MyBackend(LLM):
    def complete(self, messages, model=None): ...

    async def acomplete(self, messages, model=None): ...


cli.make_llm = MyBackend
cli.app()
```

The test suite uses exactly this seam: `tests/conftest.py` defines a `FakeLLM` that answers from a Python function, so every command is tested end to end without the network.

## Using it as a library

```python
import asyncio
import random

from focusgroup.analyst import Analyst
from focusgroup.config import Settings
from focusgroup.llm import LLM
from focusgroup.project import Project
from focusgroup.simulation import Simulation

llm = LLM(Settings.load())
project = Project("examples/fernando")
panel = project.sample_personas(6, random.Random(1))
results = asyncio.run(Simulation(llm).run(panel, "What did your plants cost you last year?", depth=1))
print(Analyst(llm).report({"question": "...", "results": results}))
```

## Development

```bash
git clone https://github.com/joey12725/focusgroup && cd focusgroup
uv venv && uv pip install -e ".[dev]"
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
