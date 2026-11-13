"""On-disk layout of a focusgroup project.

Everything is plain files so you can read, diff and commit it::

    projects/<name>/
        brief.md          the product description you gave `init`
        blueprint.yaml    the persona DSL (edit freely)
        personas/         p_001.md, p_002.md, ... (YAML front matter + backstory)
        sessions/         session_<timestamp>.json, one per `ask` or `batch` run
        reports/          report_<timestamp>.md, saved by `analyze --save`
"""

from __future__ import annotations

import datetime as dt
import json
import random
import re
from pathlib import Path
from typing import Any

import yaml

TIMESTAMP = re.compile(r"(\d{8}_\d{6}(?:_\d+)?)")


class ProjectError(FileNotFoundError):
    pass


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


class Project:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @classmethod
    def resolve(cls, name_or_path: str, projects_dir: str | Path = "projects") -> Project:
        """Accept a bare project name (looked up in ``projects_dir``) or a path."""
        candidate = Path(name_or_path)
        if (candidate / "blueprint.yaml").is_file() or (candidate / "personas").is_dir():
            return cls(candidate)
        return cls(Path(projects_dir) / name_or_path)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def blueprint_path(self) -> Path:
        return self.path / "blueprint.yaml"

    @property
    def personas_dir(self) -> Path:
        return self.path / "personas"

    @property
    def sessions_dir(self) -> Path:
        return self.path / "sessions"

    @property
    def reports_dir(self) -> Path:
        return self.path / "reports"

    def exists(self) -> bool:
        return self.path.is_dir()

    def require(self) -> Project:
        if not self.exists():
            raise ProjectError(f"Project not found: {self.path}")
        return self

    # Blueprint -------------------------------------------------------------
    def load_blueprint(self) -> dict:
        if not self.blueprint_path.is_file():
            raise ProjectError(f"No blueprint.yaml in {self.path}. Run `focusgroup init` first.")
        data = yaml.safe_load(self.blueprint_path.read_text())
        if not isinstance(data, dict):
            raise ProjectError(f"{self.blueprint_path} must be a YAML mapping")
        return data

    def save_blueprint(self, content: str, brief: str | None = None) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        self.blueprint_path.write_text(content.rstrip() + "\n")
        if brief:
            (self.path / "brief.md").write_text(brief.rstrip() + "\n")
        return self.blueprint_path

    # Personas --------------------------------------------------------------
    def persona_files(self) -> list[Path]:
        if not self.personas_dir.is_dir():
            return []
        return sorted(self.personas_dir.glob("*.md"))

    def next_persona_index(self) -> int:
        numbers = [int(m.group(1)) for p in self.persona_files() if (m := re.match(r"p_(\d+)", p.stem))]
        return max(numbers, default=0) + 1

    def save_persona(self, index: int, content: str) -> Path:
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        path = self.personas_dir / f"p_{index:03d}.md"
        path.write_text(content.rstrip() + "\n")
        return path

    def sample_personas(self, count: int, rng: random.Random | None = None) -> list[dict[str, str]]:
        files = self.persona_files()
        rng = rng or random.Random()
        chosen = rng.sample(files, min(count, len(files)))
        return [{"filename": p.name, "content": p.read_text()} for p in chosen]

    # Sessions --------------------------------------------------------------
    def save_session(self, data: dict[str, Any], kind: str = "session") -> Path:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        stamp = data.setdefault("timestamp", timestamp())
        path = self.sessions_dir / f"{kind}_{stamp}.json"
        n = 1
        while path.exists():
            n += 1
            path = self.sessions_dir / f"{kind}_{stamp}_{n}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return path

    def session_files(self) -> list[Path]:
        if not self.sessions_dir.is_dir():
            return []

        def key(p: Path) -> tuple[str, float]:
            m = TIMESTAMP.search(p.stem)
            return (m.group(1) if m else "", p.stat().st_mtime)

        return sorted(self.sessions_dir.glob("*.json"), key=key)

    def load_session(self, session: str = "latest") -> tuple[Path, dict]:
        if session == "latest":
            files = self.session_files()
            if not files:
                raise ProjectError(f"No sessions yet in {self.sessions_dir}. Run `focusgroup ask` first.")
            path = files[-1]
        else:
            path = Path(session)
            if not path.is_file():
                name = session if session.endswith(".json") else f"{session}.json"
                path = self.sessions_dir / name
            if not path.is_file():
                raise ProjectError(f"Session not found: {session}")
        return path, json.loads(path.read_text())

    def save_report(self, content: str, stamp: str | None = None) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / f"report_{stamp or timestamp()}.md"
        path.write_text(content.rstrip() + "\n")
        return path
