# Command reference

Every command takes a project name (looked up in `--projects-dir`, default `./projects`) or a path to a project folder.

```bash
focusgroup [--projects-dir DIR] [--config FILE] COMMAND ...
```

## `init`: design the crowd

```bash
focusgroup init fernando --brief brief.md
focusgroup init fernando --desc "A soil sensor that texts you as your plant."
```

The Architect reads the brief and writes `projects/fernando/blueprint.yaml`. Open it and adjust the odds before you generate anyone. Use `--force` to replace an existing blueprint.

## `generate`: cast the personas

```bash
focusgroup generate fernando --count 40 --seed 7
```

| Option | Default | |
|---|---|---|
| `--count, -n` | 20 | Personas to add. Numbering continues after existing ones. |
| `--seed` | random | Makes the demographic mix reproducible. |

## `personas`: see who showed up

```bash
focusgroup personas fernando
focusgroup personas fernando --show Age --show Plants_Killed_Last_Year --show Current_Mood
```

## `ask`: run interviews

```bash
focusgroup ask fernando "Tell me about the last plant you lost." --sample 12 --depth 2
```

| Option | Default | |
|---|---|---|
| `--sample, -s` | 10 | Personas per run, drawn at random. |
| `--depth` | 0 | Improvised follow-up questions after the scripted ones. |
| `--mom` | off | Rewrite the question(s) with The Mom Test first. |
| `--option, -o` | | Split-test variant. Repeat for each variant. Needs `***` in the question. |
| `--runs` | 1 | Repeat with a fresh sample each time; all results go in one session. |
| `--seed` | random | Seeds sampling and model assignment. |

### Scripted sequences

Separate questions with `|||` to ask them in order, then let `--depth` improvise:

```bash
focusgroup ask fernando "How do you water your plants today? ||| What did that cost you last year?" --depth 1
```

### Moderator-written questions

`AGENT(...)` (or `ASSISTANT(...)`) hands one slot to a moderator model, which writes the question from your instruction and the conversation so far:

```bash
focusgroup ask fernando "What's the most annoying gadget you own? ||| AGENT(Ask whether a talking plant sensor would join that list, referencing their answer)"
```

### Split tests

```bash
focusgroup ask fernando "Fernando costs ***. Would you buy one?" \
  --option '$49 once' --option '$29 plus $3 a month' --sample 20
```

Personas are dealt round-robin across variants from a random sample. Use single quotes around dollar signs so your shell leaves them alone.

### The Mom Test

```bash
focusgroup ask fernando "Would you buy a smart plant sensor?" --mom
```

Rewrites the question into something like *"When did a plant of yours last die, and what was going on that week?"* before anyone hears it. The original and the rewrite are both printed.

## `batch`: a whole interview guide

```yaml
# examples/fernando/batch.yaml
- question: "Tell me about the last houseplant you lost. What happened?"

- question: "Fernando costs ***. Would you buy one? Be honest."
  options: ["$49 once", "$29 plus $3 a month"]

- question:
    - "How do you remember to water your plants today?"
    - "AGENT(Based on their answer, ask what they would pay to never think about it again)"
```

```bash
focusgroup batch fernando examples/fernando/batch.yaml --sample 8 --depth 1
```

Every test gets a fresh random sample. Results land in one `batch_<timestamp>.json`.

## `analyze`: get the verdict

```bash
focusgroup analyze fernando              # newest session
focusgroup analyze fernando --save       # also write reports/report_<timestamp>.md
focusgroup analyze fernando --session session_20261113_143143
```

Prints the exact tally (interviews, exchanges, per-variant counts, models used), then the Analyst's report. See [architecture.md](architecture.md#5-aggregation-analystpy) for the rubrics.
