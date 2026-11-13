"""End-to-end CLI runs against a scripted model."""

import json

import pytest
from typer.testing import CliRunner

from focusgroup import cli

from .conftest import FakeLLM, system_text

BLUEPRINT = 'Age: "{{ range(25, 60) }}"\nPlants_Owned: "{{ range(1, 40) }}"\nMood: "{{ choice(Sunny, Wilted) }}"\n'


def scripted(messages, model):
    system = system_text(messages)
    if "The Architect" in system:
        return "```yaml\n" + BLUEPRINT + "```"
    if "novelist" in system:
        return "---\nname: Test Person\nAge: 30\nPlants_Owned: 3\nMood: Sunny\nskepticism: 40\n---\nA person."
    if "Mom Test" in system:
        return "When did a plant of yours last die, and what happened?"
    if "analyst" in system:
        return "## Verdict\n**Go**"
    return "I'd try it if it were cheaper."


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for var in ("FOCUSGROUP_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "FOCUSGROUP_MODELS"):
        monkeypatch.delenv(var, raising=False)
    fake = FakeLLM(scripted)
    monkeypatch.setattr(cli, "make_llm", lambda settings: fake)
    runner = CliRunner()

    def invoke(*args):
        result = runner.invoke(cli.app, ["--projects-dir", str(tmp_path / "projects"), *args])
        return result

    invoke.llm = fake
    invoke.root = tmp_path / "projects"
    return invoke


def test_full_loop(run):
    r = run("init", "fernando", "--desc", "A soil sensor that texts you as your plant.")
    assert r.exit_code == 0, r.output
    assert (run.root / "fernando" / "blueprint.yaml").read_text() == BLUEPRINT
    assert (run.root / "fernando" / "brief.md").exists()

    r = run("generate", "fernando", "--count", "4", "--seed", "1")
    assert r.exit_code == 0, r.output
    assert sorted(p.name for p in (run.root / "fernando" / "personas").iterdir()) == [
        "p_001.md",
        "p_002.md",
        "p_003.md",
        "p_004.md",
    ]

    r = run("generate", "fernando", "--count", "1")
    assert (run.root / "fernando" / "personas" / "p_005.md").exists()

    r = run("personas", "fernando")
    assert r.exit_code == 0 and "Test Person" in r.output

    r = run("ask", "fernando", "Would you pay *** a month?", "-s", "4", "-o", "$6", "-o", "$12", "--mom")
    assert r.exit_code == 0, r.output
    session = json.loads(next((run.root / "fernando" / "sessions").glob("*.json")).read_text())
    assert session["options"] == ["$6", "$12"]
    assert {r["variant"] for r in session["results"]} == {"$6", "$12"}

    r = run("analyze", "fernando", "--save")
    assert r.exit_code == 0, r.output
    assert "Go" in r.output
    assert list((run.root / "fernando" / "reports").glob("report_*.md"))


def test_batch(run, tmp_path, example_project):
    batch = tmp_path / "batch.yaml"
    batch.write_text("- question: How do you water plants today?\n- question: Pay ***?\n  options: [$6, $12]\n")
    r = run("batch", str(example_project), str(batch), "-s", "3")
    assert r.exit_code == 0, r.output
    data = json.loads(next((example_project / "sessions").glob("batch_*.json")).read_text())
    assert len(data["tests"]) == 2
    r = run("analyze", str(example_project))
    assert r.exit_code == 0, r.output
    assert "Batch Report" in r.output and "Test 2" in r.output


def test_option_without_placeholder_fails(run, example_project):
    r = run("ask", str(example_project), "No placeholder here", "-o", "A")
    assert r.exit_code == 1
    assert "placeholder" in r.output


def test_missing_project(run):
    r = run("ask", "nope", "Q")
    assert r.exit_code == 1 and "not found" in r.output


def test_init_refuses_to_overwrite(run):
    assert run("init", "p", "--desc", "x").exit_code == 0
    r = run("init", "p", "--desc", "x")
    assert r.exit_code == 1 and "--force" in r.output


def test_welcome_and_version(run):
    assert "Invent a crowd" in run().output
    assert run("--version").output.startswith("focusgroup ")
