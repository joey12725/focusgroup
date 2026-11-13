# Configuration

focusgroup talks to any **OpenAI-compatible chat completions endpoint**. The default is [OpenRouter](https://openrouter.ai), which gives you one key for models from OpenAI, Anthropic, Google, DeepSeek, xAI and others. That model variety is what makes a mixed panel possible.

Settings resolve in this order, last one wins:

1. built-in defaults
2. `focusgroup.ini` in the working directory (or `--config path/to/file.ini`)
3. environment variables (a `.env` file in the working directory is loaded automatically)

## Quick setup

```bash
echo 'OPENROUTER_API_KEY=sk-or-v1-...' > .env
```

That is enough. The default model is `openai/gpt-5-mini` via OpenRouter.

## Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `FOCUSGROUP_API_KEY` | API key (checked first) | |
| `OPENROUTER_API_KEY` | API key (checked second) | |
| `OPENAI_API_KEY` | API key (checked third) | |
| `FOCUSGROUP_BASE_URL` | Chat completions base URL | `https://openrouter.ai/api/v1` |
| `FOCUSGROUP_MODELS` | Comma-separated interview pool. The first model also writes blueprints and personas | `openai/gpt-5-mini` |
| `FOCUSGROUP_ANALYST_MODEL` | Model for the final report | first model in the pool |
| `FOCUSGROUP_CONCURRENCY` | Max simultaneous requests | `8` |
| `FOCUSGROUP_PROJECTS` | Projects directory (same as `--projects-dir`) | `./projects` |

## `focusgroup.ini`

Copy [`focusgroup.example.ini`](../focusgroup.example.ini) to `focusgroup.ini`:

```ini
[provider]
base_url = https://openrouter.ai/api/v1
api_key_env = OPENROUTER_API_KEY
models = openai/gpt-5-mini, anthropic/claude-haiku-4.5, google/gemini-2.5-flash, deepseek/deepseek-chat-v3-0324
analyst_model = anthropic/claude-sonnet-4.5
concurrency = 8
```

`api_key_env` names the variable that holds the key, so the file itself never contains a secret and is safe to commit.

## Picking models

- **Interview pool (`models`).** Each interview picks a model from the pool at random. Several cheap, fast models from different labs give you a more varied room than one big model playing every part, because each model family has its own house style.
- **Writer.** Persona writing uses the first model in the pool. Put your most creative cheap model first.
- **Analyst (`analyst_model`).** One call per test reads every transcript, so this is the place for a stronger model.

## Other providers

Anything that speaks the OpenAI chat API works.

**OpenAI directly**

```bash
export FOCUSGROUP_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...
export FOCUSGROUP_MODELS=gpt-5-mini
```

**Local models with Ollama**

```bash
export FOCUSGROUP_BASE_URL=http://localhost:11434/v1
export FOCUSGROUP_API_KEY=ollama        # any non-empty string
export FOCUSGROUP_MODELS=llama3.1:8b,qwen2.5:7b
export FOCUSGROUP_CONCURRENCY=2
```

LM Studio (`http://localhost:1234/v1`), vLLM, LiteLLM proxies and Azure OpenAI-compatible gateways are configured the same way.

## Cost tracking

Every command ends with a line like:

```
24 LLM calls · 7,850 tokens in · 744 tokens out · $0.0054
```

When the provider reports cost per request (OpenRouter does), that number is used. Otherwise focusgroup estimates it from the table in [`focusgroup/costs.py`](../focusgroup/costs.py).
