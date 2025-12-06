1. System ArchitectureThe system operates on a "Hybrid Generation" model to ensure statistical control while maximizing narrative depth.The Architect (LLM): Translates high-level user intent into a strict mathematical configuration (The Blueprint).The Engine (Python): Executes the Blueprint using deterministic math to create "Persona Skeletons" (e.g., Age: 24, Stress: High, Brand_Affinity: Low). This guarantees the demographic distribution matches the user's request.The Writer (LLM): Takes the "Skeleton" and hallucinates the narrative flesh, explaining why the data points exist (e.g., "Stress is high because his car broke down yesterday").The Analyst (LLM): Interrogates the generated personas and synthesizes the results.2. Directory Structure & File StandardsThe system uses a flat-file database approach for portability and transparency.Plaintext/vibetest
├── main.py                 # Entry point (Typer app)
├── requirements.txt        # rich, typer, openai, pyyaml
├── config.ini              # OPENROUTER_API_KEY
│
└── /projects
    └── /fintech_saas
        ├── blueprint.yaml  # The DNA of the customer base
        ├── /personas       # Generated Markdown files
        │   ├── p_001.md
        │   └── ...
        └── /sessions       # Interview logs & Synthesis reports
            ├── session_20251205_1400.json
            └── report_20251205_1400.md
The Persona File Standard (.md)Personas are saved as Markdown with YAML Frontmatter for queryable metadata.Markdown---
uuid: "a1b2-c3d4"
name: "Marcus Cole"
# --- HARD DATA (From Python Blueprint) ---
age: 28
income: 85000
role: "Data Analyst"
location: "Austin, TX"
# --- BRAND VARIABLES (From Blueprint) ---
tech_savviness: "High"
skepticism_level: "Extreme"
purchase_driver: "Efficiency"
# --- LIFE RANDOMIZERS (From Blueprint) ---
current_mood: "Burned Out"
recent_event: "Rent increased by $200"
---

# 🧬 Psychographic Profile
**"I don't need another dashboard; I need fewer meetings."**

## 🏠 The Context
Marcus is currently living in a state of high stress. His rent just went up (see metadata), forcing him to cut his discretionary budget. He is looking for tools that save him time, not "cool tech" to play with.

## 🧠 Brand Perception
Because his skepticism is "Extreme," he views AI tools as vaporware until proven otherwise. He hates sales jargon.
3. The Blueprint DSL (Domain Specific Language)To achieve the requirement of "AI defined distributions," the system uses a custom logic parser within the YAML blueprint.File: blueprint.yamlParser Logic: When generating, Python parses strings inside {{ }} and executes the corresponding function.FunctionDescriptionExamplerange(min, max)Uniform integer selection{{ range(25, 45) }}choice(A, B, C)Simple random selection{{ choice('Male', 'Female') }}weighted(Key:Val)Weighted probability{{ weighted('Admin': 0.8, 'Manager': 0.2) }}normal(mean, std)Bell curve distribution{{ normal(75000, 15000) }}bool(chance)Boolean with probability{{ bool(0.3) }} (30% True)4. Feature SpecificationsFeature A: init (The Architect)Command: personas init "Project Name" --desc "Description"Prompt: Sends the description to the Architect LLM (e.g., Claude 3.5 Sonnet).Task: "Analyze this product. Determine 3-5 crucial psychographic variables that would impact a buying decision (e.g., 'Risk Tolerance', 'Tech Stack', 'Aesthetic Taste'). Create a blueprint.yaml using the permitted DSL functions."Output: Writes blueprint.yaml to the project folder.UX:[green]✓ Blueprint created![/green] Defined variables: Budget, Risk_Tolerance, Legacy_Systems.Feature B: generate (The Factory)Command: personas generate --count 50 --project "Project Name"Hydration (Python):Load blueprint.yaml.Loop 50 times.For each iteration, execute the DSL math.Result: A dictionary of raw stats: {'age': 32, 'mood': 'Angry', ...}.Narration (LLM):Send the raw stats dictionary to the Writer LLM (e.g., Llama-3-70b or Liquid).System Prompt: "You are a creative writer. I will give you a skeleton of a person. You must breathe life into them. Connect the dots. If they are 'Angry' and 'Broke', invent a scenario explaining why."Output: Saves 50 individual .md files.UX: Uses rich.progress to show a dual progress bar (Math generation vs. LLM Writing).Feature C: ask (The Simulation)Command: personas ask "Question" --sample 10 --project "Project Name"Sampling: Randomly selects 10 .md files from the target folder.Context Loading: Reads the content of each file.Parallel Execution: Uses asyncio to hit OpenRouter with 10 concurrent requests.Prompt: "Roleplay as the person defined below. Answer the user's question honestly based on your 'Current Mood' and 'Financial Situation'. Be brief."Output: Streams responses to the CLI and saves a JSON log to /sessions.UX:[bold cyan]User:[/bold cyan] "Would you pay $50/mo for this?"[bold yellow]Marcus (28):[/bold yellow] "No way. My rent just went up. Maybe $20."[bold yellow]Sarah (45):[/bold yellow] "Yes, if it saves me an hour a week. Time is money."Feature D: synthesize (The Insight)Command: personas analyze --session latestInput: Loads the JSON log from the last ask session.Processing: Sends all Q&A pairs to the Analyst LLM (Claude 3.5 Sonnet).Task:Identify the Consensus (60%+ agreement).Identify the Variance (Major points of contention).Identify Outliers.Provide a "Go/No-Go" recommendation.Output: Renders a beautiful Markdown table in the terminal and saves it.5. Implementation RoadmapPhase 1: The Core (Day 1)[ ] Set up Typer app skeleton.[ ] Implement the BlueprintParser class (the Python logic that processes the {{ weighted() }} syntax).[ ] Create the PersonaGenerator class that merges the Blueprint with the OpenRouter API.Phase 2: The Interface (Day 2)[ ] Implement init command with the Architect prompt.[ ] Implement generate command with rich progress bars.[ ] Ensure file I/O works (saving/loading MD files).Phase 3: The Brain (Day 3)[ ] Implement ask using asyncio for speed (don't wait for personas one by one).[ ] Implement analyze with a strong analytical system prompt.[ ] Polish the CLI output (colors, tables, emojis).6. Recommended LLM RoutingUse openai python library pointing to https://openrouter.ai/api/v1
Use the model google/gemini-2.5-flash-lite-preview-09-2025 to start