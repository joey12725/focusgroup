"""Command-line interface."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import Any, NoReturn, Optional

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from . import __version__
from .analyst import Analyst, session_tests, tally
from .architect import Architect
from .config import Settings
from .llm import LLM
from .mom_test import MomTest
from .persona_generator import PersonaGenerator
from .project import Project, ProjectError, timestamp
from .simulation import AGENT_TAG, PLACEHOLDER, Simulation, front_matter, has_placeholder

app = typer.Typer(
    help="Synthetic customer interviews: generate a crowd of personas, interview them in parallel, get a verdict.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


class State:
    projects_dir: Path = Path("projects")
    settings: Settings | None = None


state = State()


def make_llm(settings: Settings) -> LLM:
    """Factory seam: tests and custom backends swap this out."""
    if not settings.api_key:
        fail(
            "No API key found. Put OPENROUTER_API_KEY=... in a .env file here, or set FOCUSGROUP_API_KEY. "
            "See docs/configuration.md for other providers."
        )
    return LLM(settings)


def get_llm() -> LLM:
    return make_llm(state.settings or Settings.load())


def fail(message: str) -> NoReturn:
    console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(1)


def open_project(name: str) -> Project:
    project = Project.resolve(name, state.projects_dir)
    if not project.exists():
        fail(f"Project '{name}' not found in {state.projects_dir}/. Run `focusgroup init {name}` first.")
    return project


def print_cost(llm: LLM) -> None:
    if llm.costs.calls:
        console.print(f"[dim]{llm.costs.summary()}[/dim]")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"focusgroup {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    projects_dir: Path = typer.Option(
        Path("projects"), "--projects-dir", envvar="FOCUSGROUP_PROJECTS", help="Where projects live."
    ),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to a focusgroup.ini file."),
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
) -> None:
    """[bold magenta]focusgroup[/bold magenta]: a focus group in your terminal."""
    load_dotenv(Path.cwd() / ".env")
    state.projects_dir = projects_dir
    try:
        state.settings = Settings.load(config)
    except FileNotFoundError as exc:
        fail(str(exc))
    if ctx.invoked_subcommand is None:
        text = Text("focusgroup", style="bold magenta", justify="center")
        text.append("\n\nInvent a crowd. Ask it anything. Get a verdict.\n\n", style="default")
        text.append('focusgroup init my-idea --desc "..."\n', style="cyan")
        text.append("focusgroup generate my-idea --count 30\n", style="cyan")
        text.append('focusgroup ask my-idea "How do you handle X today?"\n', style="cyan")
        text.append("focusgroup analyze my-idea\n\n", style="cyan")
        text.append("focusgroup --help for everything else", style="dim")
        console.print(Panel(text, border_style="magenta", expand=False))


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name (a folder under the projects dir)."),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Product description."),
    brief: Optional[Path] = typer.Option(None, "--brief", "-b", help="Read the product description from a file."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing blueprint."),
) -> None:
    """Have the Architect design a persona blueprint from your product brief."""
    if brief:
        if not brief.is_file():
            fail(f"Brief file not found: {brief}")
        desc = brief.read_text()
    if not desc:
        fail('Describe the product with --desc "..." or --brief brief.md')
    project = Project(state.projects_dir / name)
    if project.blueprint_path.exists() and not force:
        fail(f"{project.blueprint_path} already exists. Use --force to replace it.")

    console.print(
        Panel(
            f"[bold]{escape(name)}[/bold]\n[dim]{escape(desc.strip()[:400])}[/dim]",
            title="New project",
            border_style="blue",
        )
    )
    llm = get_llm()
    with console.status("[bold green]The Architect is drafting your blueprint...", spinner="dots"):
        try:
            content = Architect(llm).create_blueprint(name, desc)
        except Exception as exc:
            fail(f"Could not build a valid blueprint: {exc}")
    path = project.save_blueprint(content, brief=desc)

    variables = list(yaml.safe_load(content).keys())
    console.print(
        Panel(
            f"[bold green]Blueprint saved[/bold green] to {path}\n"
            f"[dim]{len(variables)} variables:[/dim] {', '.join(variables)}\n\n"
            f"Tweak it if you like, then run [bold]focusgroup generate {name}[/bold]",
            border_style="green",
        )
    )
    print_cost(llm)


@app.command()
def generate(
    project_name: str = typer.Argument(..., metavar="PROJECT"),
    count: int = typer.Option(20, "--count", "-n", help="How many personas to add."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed the demographic dice for a reproducible mix."),
) -> None:
    """Roll skeletons from the blueprint and have the LLM write each persona."""
    project = open_project(project_name)
    llm = get_llm()
    generator = PersonaGenerator(project, llm, seed=seed)
    try:
        project.load_blueprint()
    except ProjectError as exc:
        fail(str(exc))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]Casting {count} personas", total=count)
        try:
            names = asyncio.run(generator.generate(count, on_done=lambda _i: progress.advance(task)))
        except Exception as exc:
            fail(f"Persona generation failed: {exc}")

    console.print(
        f"[bold green]Cast {len(names)} personas[/bold green] into {project.personas_dir} "
        f"({len(project.persona_files())} total)"
    )
    print_cost(llm)


@app.command()
def personas(
    project_name: str = typer.Argument(..., metavar="PROJECT"),
    limit: int = typer.Option(15, "--limit", help="Rows to show."),
    fields: int = typer.Option(4, "--fields", help="How many blueprint fields to show per persona."),
    show: Optional[list[str]] = typer.Option(None, "--show", help="Show these blueprint fields. Repeatable."),
) -> None:
    """List the cast: who is in this project's persona pool."""
    project = open_project(project_name)
    files = project.persona_files()
    if not files:
        fail(f"No personas yet. Run `focusgroup generate {project_name}`.")
    rows = [(p.stem, front_matter(p.read_text())) for p in files[:limit]]
    keys = show or [k for k in rows[0][1] if k.lower() not in {"name", "skepticism"}][:fields]

    table = Table(title=f"{project.name}: {len(files)} personas", header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    for key in keys:
        table.add_column(key.replace("_", " "))
    table.add_column("Skepticism", justify="right")
    for stem, meta in rows:
        table.add_row(
            stem,
            str(meta.get("name", "")),
            *[str(meta.get(k, "")).replace("_", " ") for k in keys],
            str(meta.get("skepticism", "")),
        )
    console.print(table)


def parse_question(question: str) -> str | list[str]:
    if "|||" in question:
        return [q.strip() for q in question.split("|||") if q.strip()]
    return question


def show_question(question: str | list[str]) -> str:
    questions = question if isinstance(question, list) else [question]
    lines = []
    for i, q in enumerate(questions, 1):
        match = AGENT_TAG.match(q.strip())
        shown = f"[italic]moderator writes:[/italic] {escape(match.group(1))}" if match else escape(q)
        lines.append(f"[bold]{i}.[/bold] {shown}" if len(questions) > 1 else shown)
    return "\n".join(lines)


def results_table(results: list[dict[str, Any]], split: bool) -> Table:
    table = Table(title="Interviews", show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("Persona", style="cyan", max_width=24)
    if split:
        table.add_column("Variant", style="yellow", max_width=16)
    table.add_column("Conversation")
    for r in results:
        lines = []
        for i, turn in enumerate(r.get("conversation", [])):
            if turn["role"] == "persona":
                lines.append(escape(turn["content"]))
            elif i > 0:  # the opening question is already on screen
                lines.append(f"[dim italic]> {escape(turn['content'])}[/dim italic]")
        if r["status"] != "success":
            lines.append(f"[red]{escape(r.get('error', 'failed'))}[/red]")
        name = f"{r.get('persona_name', r['persona'])}\n[dim]{r.get('model', '').split('/')[-1]}[/dim]"
        table.add_row(name, *([str(r.get("variant"))] if split else []), "\n".join(lines))
    return table


@app.command()
def ask(
    project_name: str = typer.Argument(..., metavar="PROJECT"),
    question: str = typer.Argument(..., help="The question. Separate a scripted sequence with |||."),
    sample: int = typer.Option(10, "--sample", "-s", help="Personas to interview per run."),
    depth: int = typer.Option(0, "--depth", help="Improvised follow-ups after the scripted questions."),
    mom: bool = typer.Option(False, "--mom", help="Rewrite the question with The Mom Test first."),
    options: Optional[list[str]] = typer.Option(
        None, "--option", "-o", help=f"Split-test variant to substitute for {PLACEHOLDER}. Repeat for each variant."
    ),
    runs: int = typer.Option(1, "--runs", help="Repeat with a fresh random sample each time."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed persona sampling and model assignment."),
) -> None:
    """Interview a random sample of personas, in parallel."""
    project = open_project(project_name)
    if not project.persona_files():
        fail(f"No personas yet. Run `focusgroup generate {project_name}`.")
    q = parse_question(question)
    if options and not has_placeholder(q):
        fail(f"--option needs a {PLACEHOLDER} placeholder in the question to swap variants into.")

    llm = get_llm()
    if mom:
        with console.status("[bold yellow]Applying The Mom Test...", spinner="dots"):
            rewritten = MomTest(llm).rewrite_all(q)
        console.print(
            Panel(
                f"[dim]{show_question(q)}[/dim]\n[bold green]{show_question(rewritten)}[/bold green]",
                title="The Mom Test",
                border_style="green",
            )
        )
        q = rewritten

    setup = [f"[bold]{project.name}[/bold] · {sample} personas" + (f" × {runs} runs" if runs > 1 else "")]
    if depth:
        setup.append(f"{depth} follow-up" + ("s" if depth > 1 else ""))
    if options:
        setup.append("split test: " + " vs ".join(f"[yellow]{escape(o)}[/yellow]" for o in options))
    console.print(Panel(show_question(q), title=" · ".join(setup), border_style="yellow"))

    rng = random.Random(seed)
    sim = Simulation(llm, rng=rng)
    results: list[dict] = []
    for run in range(runs):
        label = f" (run {run + 1}/{runs})" if runs > 1 else ""
        with console.status(f"[bold yellow]Interviewing{label}...", spinner="earth"):
            panel = project.sample_personas(sample, rng)
            results += asyncio.run(sim.run(panel, q, depth=depth, options=options))

    console.print(results_table(results, split=bool(options)))
    counts = tally(results)
    path = project.save_session(
        {
            "type": "single",
            "timestamp": timestamp(),
            "question": q,
            "options": options,
            "depth": depth,
            "results": results,
        }
    )
    console.print(f"[dim]{counts['succeeded']}/{counts['interviews']} interviews saved to {path}[/dim]")
    console.print(f"Next: [bold]focusgroup analyze {project_name}[/bold]")
    print_cost(llm)


@app.command()
def batch(
    project_name: str = typer.Argument(..., metavar="PROJECT"),
    batch_file: Path = typer.Argument(..., help="YAML list of tests: question, optional options."),
    sample: int = typer.Option(10, "--sample", "-s", help="Personas per test."),
    depth: int = typer.Option(0, "--depth", help="Improvised follow-ups per interview."),
    mom: bool = typer.Option(False, "--mom", help="Apply The Mom Test to every question."),
    seed: Optional[int] = typer.Option(None, "--seed"),
) -> None:
    """Run several tests back to back, each with a fresh sample."""
    project = open_project(project_name)
    if not batch_file.is_file():
        fail(f"Batch file not found: {batch_file}")
    tests = yaml.safe_load(batch_file.read_text())
    if not isinstance(tests, list) or not all(isinstance(t, dict) and t.get("question") for t in tests):
        fail("Batch file must be a YAML list of {question: ..., options: [...]} entries.")

    llm = get_llm()
    rng = random.Random(seed)
    sim = Simulation(llm, rng=rng)
    mom_test = MomTest(llm) if mom else None
    done: list[dict] = []
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), console=console
    ) as progress:
        task = progress.add_task("[magenta]Running tests", total=len(tests))
        for i, test in enumerate(tests, 1):
            q = test["question"]
            q = q if isinstance(q, list) else parse_question(q)
            options = test.get("options")
            progress.update(task, description=f"[magenta]Test {i}/{len(tests)}")
            if mom_test:
                q = mom_test.rewrite_all(q)
            panel = project.sample_personas(sample, rng)
            results = asyncio.run(sim.run(panel, q, depth=depth, options=options))
            done.append({"question": q, "options": options, "results": results})
            progress.advance(task)

    path = project.save_session({"type": "batch", "timestamp": timestamp(), "tests": done}, kind="batch")
    console.print(f"[bold green]Batch complete[/bold green]: {len(done)} tests saved to {path}")
    print_cost(llm)


@app.command()
def analyze(
    project_name: str = typer.Argument(..., metavar="PROJECT"),
    session: str = typer.Option("latest", "--session", help="Session file name, path, or 'latest'."),
    save: bool = typer.Option(False, "--save", help="Also write the report to reports/."),
) -> None:
    """Synthesize a session into consensus, variance, outliers and a verdict."""
    project = open_project(project_name)
    try:
        path, data = project.load_session(session)
    except ProjectError as exc:
        fail(str(exc))

    for test in session_tests(data):
        c = tally(test["results"])
        line = f"[bold]{c['succeeded']}[/bold] interviews · {c['turns']} exchanges"
        if c["variants"]:
            line += " · " + " vs ".join(f"{v} ({n})" for v, n in c["variants"].items())
        if len(c["models"]) > 1:
            line += f" · {len(c['models'])} models"
        if c["failed"]:
            line += f" · [red]{c['failed']} failed[/red]"
        console.print(line)

    llm = get_llm()
    with console.status("[bold cyan]The Analyst is reading transcripts...", spinner="dots"):
        report = Analyst(llm).report(data)
    console.print(Panel(Markdown(report), title=f"Report · {path.name}", border_style="magenta"))
    if save:
        out = project.save_report(report, data.get("timestamp"))
        console.print(f"[dim]Saved to {out}[/dim]")
    print_cost(llm)


if __name__ == "__main__":  # pragma: no cover
    app()
