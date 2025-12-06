# Usage Guide

This guide covers all available commands in the VibeTest CLI.

## `init`
Initialize a new project and generate a blueprint.

```bash
python main.py init [PROJECT_NAME] --desc "[DESCRIPTION]"
```
*   **Arguments**:
    *   `PROJECT_NAME`: The name of the folder to create in `projects/`.
    *   `--desc`: A detailed description of your product or idea. The more detail, the better the Architect can design the blueprint.

## `generate`
Generate a batch of personas based on the project's blueprint.

```bash
python main.py generate [PROJECT_NAME] --count [NUMBER]
```
*   **Arguments**:
    *   `PROJECT_NAME`: The name of your project.
    *   `--count`: The number of personas to generate (Default: 50).

## `ask`
Run a simulation by asking a question to your personas.

```bash
python main.py ask "[QUESTION]" [PROJECT_NAME] [OPTIONS]
```

### Options:
*   `--sample [INT]`: Number of personas to interview (Default: 10).
*   `--depth [INT]`: Number of follow-up questions to ask. `0` means a single Q&A turn. Higher numbers allow for back-and-forth conversation.
*   `--mom`: Activates **The Mom Test** mode. Rewrites your question to be behavioral and unbiased.
*   `--runs [INT]`: Run the simulation multiple times with reshuffled groups to gather more data.
*   `--option [TEXT]`: Define variants for **Split Testing**. Requires `***` in your question text.
    *   *Example*: `python main.py ask "Would you pay ***?" my_project --option "$10" --option "$50"`

## `batch_ask`
Run multiple pre-defined tests sequentially from a YAML file.

```bash
python main.py batch_ask [PROJECT_NAME] [BATCH_FILE_PATH]
```
*   **Batch File Format**:
    ```yaml
    - question: "How do you solve X?"
    - question: "Would you pay ***?"
      options: ["$10", "$20"]
    ```

## `analyze`
Analyze the results of an interview session.

```bash
python main.py analyze [PROJECT_NAME] [OPTIONS]
```

### Options:
*   `--session [SESSION_ID]`: The ID or filename of the session to analyze. Defaults to `latest`.
*   `--save`: Saves the output report as a Markdown file in the project's `sessions/` folder.
