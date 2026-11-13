"""Provider settings: where the LLM lives and which models to use.

Resolution order, last one wins:

1. built-in defaults
2. ``focusgroup.ini`` in the working directory (or the file passed with ``--config``)
3. environment variables (a ``.env`` file in the working directory is loaded first)
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-5-mini"
DEFAULT_CONFIG_FILE = "focusgroup.ini"

# Checked in order; the first one that is set provides the API key.
API_KEY_ENV_VARS = ("FOCUSGROUP_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")


def _split_models(value: str) -> list[str]:
    return [m.strip().strip("\"'") for m in value.split(",") if m.strip().strip("\"'")]


def _clean(value: str) -> str:
    return value.strip().strip("\"'")


@dataclass
class Settings:
    """Everything needed to talk to an OpenAI-compatible chat endpoint."""

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    models: list[str] = field(default_factory=lambda: [DEFAULT_MODEL])
    analyst_model: str | None = None
    concurrency: int = 8

    @property
    def default_model(self) -> str:
        """Model used for single-shot jobs (blueprints, personas, question rewrites)."""
        return self.models[0]

    @property
    def report_model(self) -> str:
        """Model used to synthesize the final report."""
        return self.analyst_model or self.default_model

    @classmethod
    def load(cls, config_path: str | os.PathLike | None = None, env: dict | None = None) -> Settings:
        env = dict(os.environ if env is None else env)
        settings = cls()

        path = Path(config_path) if config_path else Path(DEFAULT_CONFIG_FILE)
        if path.is_file():
            parser = configparser.ConfigParser()
            parser.read(path)
            if parser.has_section("provider"):
                section = parser["provider"]
                if section.get("base_url"):
                    settings.base_url = _clean(section["base_url"])
                if section.get("models"):
                    settings.models = _split_models(section["models"])
                if section.get("analyst_model"):
                    settings.analyst_model = _clean(section["analyst_model"])
                if section.get("concurrency"):
                    settings.concurrency = section.getint("concurrency")
                key_env = section.get("api_key_env")
                if key_env and env.get(_clean(key_env)):
                    settings.api_key = env[_clean(key_env)]
        elif config_path:
            raise FileNotFoundError(f"Config file not found: {path}")

        if env.get("FOCUSGROUP_BASE_URL"):
            settings.base_url = env["FOCUSGROUP_BASE_URL"]
        if env.get("FOCUSGROUP_MODELS"):
            settings.models = _split_models(env["FOCUSGROUP_MODELS"])
        if env.get("FOCUSGROUP_ANALYST_MODEL"):
            settings.analyst_model = env["FOCUSGROUP_ANALYST_MODEL"]
        if env.get("FOCUSGROUP_CONCURRENCY"):
            settings.concurrency = int(env["FOCUSGROUP_CONCURRENCY"])

        if settings.api_key is None:
            for name in API_KEY_ENV_VARS:
                if env.get(name):
                    settings.api_key = env[name]
                    break

        if not settings.models:
            settings.models = [DEFAULT_MODEL]
        settings.concurrency = max(1, settings.concurrency)
        return settings
