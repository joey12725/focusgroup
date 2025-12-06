# Configuration

VibeTest uses a `config.ini` file in the root directory to manage settings and API keys.

## Basic Setup

Create a file named `config.ini` in the root folder with the following structure:

```ini
[API]
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Getting an API Key
VibeTest uses **OpenRouter** to access various LLMs (Claude, GPT-4, Llama 3) through a single unified API. 
1.  Go to [openrouter.ai](https://openrouter.ai).
2.  Create an account and generate an API Key.
3.  Paste it into your `config.ini`.

## Model Configuration (Optional)

By default, VibeTest comes pre-configured with recommended models. However, you can override these in the `config.ini` if you wish to experiment with different models.

```ini
[MODELS]
; The "Smart" model used for Architect and Analyst roles
ARCHITECT_MODEL=anthropic/claude-3.5-sonnet
ANALYST_MODEL=anthropic/claude-3.5-sonnet

; The "Creative" model used for writing Personas
WRITER_MODEL=meta-llama/llama-3-70b-instruct

; The "Fast" model used for parallel simulations
SIMULATION_MODEL=meta-llama/llama-3-8b-instruct
```

> [!TIP]
> Use smaller/faster models (like Llama 3 8B) for `SIMULATION_MODEL` to keep costs low and speed high when running large batches. Use "smarter" models (like Claude 3.5 Sonnet) for `ARCHITECT_MODEL` and `ANALYST_MODEL` where reasoning quality is paramount.
