import typer
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from vibetest.architect import Architect
from vibetest.persona_generator import PersonaGenerator
from vibetest.simulation import Simulation
from vibetest.analyst import Analyst
from vibetest.mom_test import MomTest
from vibetest.llm_cost_tracker import CostTracker
import asyncio
import yaml
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(help="VibeTest: AI-Powered Persona Simulation Tool")
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    VibeTest CLI - Generate, Simulate, and Analyze AI Personas.
    """
    if ctx.invoked_subcommand is None:
        welcome_text = Text("Welcome to VibeTest", justify="center", style="bold magenta")
        welcome_text.append("\n\nUse this tool to generate AI personas, run simulations, and analyze results.\n")
        welcome_text.append("Run [bold]python main.py --help[/bold] to see available commands.", style="dim")
        
        console.print(Panel(welcome_text, title="VibeTest CLI", border_style="magenta", expand=False))

@app.command()
def init(name: str, desc: str = typer.Option(..., help="Description of the project")):
    """
    Initialize a new persona project with a blueprint.
    """
    console.print(Panel(f"[bold]Initializing Project:[/bold] {name}\n[dim]{desc}[/dim]", title="Init", border_style="blue"))
    
    architect = Architect()
    
    with console.status("[bold green]Architect is designing the blueprint...[/bold green]", spinner="dots"):
        blueprint_content = architect.create_blueprint(name, desc)
        filepath = architect.save_blueprint(name, blueprint_content)
    
    success_text = Text()
    success_text.append("✓ Blueprint created successfully!\n", style="bold green")
    success_text.append(f"Saved to: {filepath}\n\n")
    success_text.append("Next Steps:", style="bold underline")
    success_text.append(f"\n1. Review {filepath}")
    success_text.append(f"\n2. Run [bold]python main.py generate {name}[/bold]")
    
    console.print(Panel(success_text, title="Success", border_style="green"))

@app.command()
def generate(project: str, count: int = 50):
    """
    Generate personas based on the blueprint.
    """
    project_path = os.path.join("projects", project)
    if not os.path.exists(project_path):
        console.print(f"[red]Project '{project}' not found![/red]")
        return

    console.print(Panel(f"Generating [bold]{count}[/bold] personas for project: [bold cyan]{project}[/bold cyan]", title="Generate", border_style="cyan"))
    
    generator = PersonaGenerator(project_path)
    try:
        blueprint = generator.load_blueprint()
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] blueprint.yaml not found in {project_path}!")
        return

    async def generate_single_persona(index: int, semaphore: asyncio.Semaphore, progress, task_id):
        async with semaphore:
            # 1. Generate Skeleton (Math)
            skeleton = generator.generate_skeleton(blueprint)
            
            # 2. Flesh out (LLM)
            persona_content = await generator.async_flesh_out_persona(skeleton)
            
            # 3. Save
            filename = f"p_{index+1:03d}.md"
            generator.save_persona(persona_content, filename)
            
            progress.advance(task_id)

    async def run_generation():
        # Limit concurrency to 10 to avoid hitting rate limits too hard
        semaphore = asyncio.Semaphore(10)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]Forging {count} personas (Parallel)...", total=count)
            
            tasks = []
            for i in range(count):
                tasks.append(generate_single_persona(i, semaphore, progress, task))
            
            await asyncio.gather(*tasks)

    # Run the async generation
    asyncio.run(run_generation())
            
    console.print(Panel(f"[bold green]✓ Successfully generated {count} personas[/bold green]\nLocation: {project_path}/personas", title="Complete", border_style="green"))
    
    cost = CostTracker().get_total_cost()
    console.print(Panel(f"Total Cost: [bold green]${cost:.2f}[/bold green]", title="Cost", border_style="green"))

@app.command()
def ask(
    question: str, 
    project: str, 
    sample: int = typer.Option(10, help="Number of personas to interview"), 
    depth: int = typer.Option(0, help="Number of follow-up questions to ask (0 for single turn)"), 
    mom: bool = typer.Option(False, "--mom", help="Apply The Mom Test to rewrite the question"),
    options: list[str] = typer.Option(None, "--option", help="Options for split testing (requires *** in question)"),
    runs: int = typer.Option(1, "--runs", help="Number of times to run the simulation (reshuffles personas each time)")
):
    """
    Ask a question to a sample of personas.
    """
    # Configuration Panel
    config_text = Text()
    config_text.append(f"Project: {project}\n", style="bold cyan")
    config_text.append(f"Sample Size: {sample}\n", style="cyan")
    if runs > 1:
        config_text.append(f"Runs: {runs} (Total interviews: {sample * runs})\n", style="bold yellow")
    
    if depth > 0:
        config_text.append(f"Conversation Depth: {depth} follow-ups\n", style="bold yellow")
    else:
        config_text.append(f"Conversation Depth: Single Turn (Default)\n", style="dim")
        
    if mom:
        config_text.append(f"The Mom Test: Active (Rewriting question)\n", style="bold green")
    else:
        config_text.append(f"The Mom Test: Inactive\n", style="dim")
        
    if options:
        config_text.append(f"Split Testing: Active ({len(options)} variants)\n", style="bold magenta")
        config_text.append(f"Variants: {', '.join(options)}\n", style="magenta")
    else:
        config_text.append(f"Split Testing: Inactive\n", style="dim")

    console.print(Panel(config_text, title="Simulation Configuration", border_style="blue"))

    # Tips for advanced features
    if depth == 0 and not mom and not options and runs == 1:
        console.print(Panel("[dim]Tip: Try adding [bold]--depth 2[/bold] for follow-ups, [bold]--mom[/bold] for better questions, [bold]--option[/bold] for A/B testing, or [bold]--runs 2[/bold] for more data![/dim]", border_style="dim"))

    # Validate split testing
    if "|||" in question:
        question = [q.strip() for q in question.split("|||")]
    
    if options:
        # Check for placeholder in any of the questions if it's a list
        if isinstance(question, list):
            if not any("***" in q for q in question):
                console.print("[bold red]Error:[/bold red] You provided options but the '***' placeholder is missing from all questions.")
                return
        elif "***" not in question:
            console.print("[bold red]Error:[/bold red] You provided options but the question is missing the '***' placeholder.")
            return

    if mom:
        with console.status("[bold yellow]Applying The Mom Test...[/bold yellow]", spinner="dots"):
            mom_test = MomTest()
            original_question = question
            question = mom_test.rewrite_question(question)
            
        console.print(Panel(f"[dim]Original: {original_question}[/dim]\n[bold green]Rewritten: {question}[/bold green]", title="The Mom Test", border_style="green"))

    # Format question for display
    display_text = ""
    import re
    
    questions_to_display = question if isinstance(question, list) else [question]
    formatted_rows = []
    
    for idx, q_text in enumerate(questions_to_display):
        q_display = q_text
        # Check for ASSISTANT(...) or AGENT(...) syntax to replace for display
        match = re.search(r'^(?:ASSISTANT|AGENT)\((.*)\)$', q_text.strip(), re.DOTALL)
        if match:
            instruction = match.group(1)
            q_display = f"AGENT ASKS A QUESTION BASED ON THE PROMPT: {instruction}"
            
        if len(questions_to_display) > 1:
            formatted_rows.append(f"[bold]Question {idx+1}:[/bold] {q_display}")
        else:
            formatted_rows.append(f"[bold]Question:[/bold] {q_display}")
            
    console.print(Panel("\n".join(formatted_rows), title="Starting Simulation", border_style="yellow"))
    project_path = os.path.join("projects", project)
    if not os.path.exists(project_path):
        console.print(f"[bold red]Error:[/bold red] Project '{project}' not found!")
        return

    sim = Simulation(project_path)
    
    all_results = []
    
    for i in range(runs):
        run_label = f"Run {i+1}/{runs}"
        with console.status(f"[bold yellow]Conducting interviews ({run_label})...[/bold yellow]", spinner="earth"):
            run_results = asyncio.run(sim.run_simulation(question, sample, depth, options))
            all_results.extend(run_results)
            
    results = all_results
        
    if not results:
        console.print("[bold red]Simulation failed:[/bold red] No personas found or other error.")
        return

    # Display results in a table
    table = Table(title="Interview Results", show_header=True, header_style="bold magenta")
    table.add_column("Persona", style="cyan", no_wrap=True)
    if options:
        table.add_column("Variant", style="yellow")
    table.add_column("Response", style="white")

    for res in results:
        if res['status'] == 'success':
            name = res['persona'].replace('.md', '').replace('p_', 'Persona ')
            conversation = res['conversation']
            
            # Show last response or summary
            last_response = conversation[-1]['content']
            if len(conversation) > 2:
                display_text = f"[dim](...{len(conversation)-1} msgs)[/dim]\n{last_response}"
            else:
                display_text = last_response
                
            if options:
                table.add_row(name, res.get('variant', 'N/A'), display_text)
            else:
                table.add_row(name, display_text)
        else:
            if options:
                table.add_row(res['persona'], "N/A", f"[red]Error: {res.get('response', 'Unknown error')}[/red]")
            else:
                table.add_row(res['persona'], f"[red]Error: {res.get('response', 'Unknown error')}[/red]")
            
    console.print(table)
            
    # Save session
    filepath = sim.save_session(question, results)

    console.print(f"\n[dim]Session saved to: {filepath}[/dim]")

    cost = CostTracker().get_total_cost()
    console.print(Panel(f"Total Cost: [bold green]${cost:.2f}[/bold green]", title="Cost", border_style="green"))

@app.command()
def batch_ask(
    project: str,
    batch_file: str,
    sample: int = typer.Option(10, help="Number of personas to interview per test"),
    depth: int = typer.Option(0, help="Number of follow-up questions"),
    mom: bool = typer.Option(False, "--mom", help="Apply The Mom Test to all questions")
):
    """
    Run multiple tests back-to-back from a YAML file.
    """
    if not os.path.exists(batch_file):
        console.print(f"[bold red]Error:[/bold red] Batch file '{batch_file}' not found!")
        return

    project_path = os.path.join("projects", project)
    if not os.path.exists(project_path):
        console.print(f"[bold red]Error:[/bold red] Project '{project}' not found!")
        return

    try:
        with open(batch_file, 'r') as f:
            tests = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[bold red]Error loading batch file:[/bold red] {e}")
        return

    if not isinstance(tests, list):
        console.print("[bold red]Error:[/bold red] Batch file must contain a list of tests.")
        return

    console.print(Panel(f"Running [bold]{len(tests)}[/bold] tests from {batch_file}\nProject: {project}\nSample Size: {sample}", title="Batch Simulation", border_style="magenta"))

    sim = Simulation(project_path)
    batch_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False
    ) as progress:
        overall_task = progress.add_task(f"[magenta]Running Batch...", total=len(tests))
        
        for i, test in enumerate(tests):
            question = test.get('question')
            options = test.get('options')
            
            if not question:
                console.print(f"[yellow]Skipping test {i+1}: No question provided.[/yellow]")
                progress.advance(overall_task)
                continue

            progress.update(overall_task, description=f"[magenta]Test {i+1}/{len(tests)}: {question[:30]}...")
            
            # Apply Mom Test if requested
            if mom:
                mom_test = MomTest()
                question = mom_test.rewrite_question(question)

            # Run Simulation
            # We use a new set of random personas for each test (as per requirement "reshuffle")
            # run_simulation does this by calling load_random_personas internally
            results = asyncio.run(sim.run_simulation(question, sample, depth, options))
            
            batch_results.append({
                "question": question,
                "options": options,
                "results": results,
                "is_split_test": bool(options)
            })
            
            progress.advance(overall_task)

    # Save Batch Session
    filepath = sim.save_batch_session(batch_results)
    
    console.print(Panel(f"[bold green]✓ Batch Simulation Complete[/bold green]\n\nSaved to: {filepath}", title="Success", border_style="green"))
    
    cost = CostTracker().get_total_cost()
    console.print(Panel(f"Total Cost: [bold green]${cost:.2f}[/bold green]", title="Cost", border_style="green"))


@app.command()
def analyze(
    project: str, 
    session: str = "latest",
    save: bool = typer.Option(False, "--save", help="Save the analysis report as a markdown file")
):
    """
    Analyze the results of a session.
    """
    console.print(Panel(f"Analyzing session: [bold]{session}[/bold] in project: [bold]{project}[/bold]", title="Analyst", border_style="magenta"))
    project_path = os.path.join("projects", project)
    if not os.path.exists(project_path):
        console.print(f"[red]Project '{project}' not found![/red]")
        return

    analyst = Analyst(project_path)
    
    session_data = analyst.load_session(session)
    if not session_data:
        console.print(f"[red]Session '{session}' not found in {project_path}/sessions![/red]")
        return

    with console.status("[bold cyan]Analyzing results...[/bold cyan]"):
        report = analyst.analyze_results(session_data)
        
    analyst.render_report(report)

    if save:
        filepath = analyst.save_report(report, session_data)
        console.print(f"\n[dim]Report saved to: {filepath}[/dim]")
    
    cost = CostTracker().get_total_cost()
    console.print(Panel(f"Total Cost: [bold green]${cost:.2f}[/bold green]", title="Cost", border_style="green"))

if __name__ == "__main__":
    app()
