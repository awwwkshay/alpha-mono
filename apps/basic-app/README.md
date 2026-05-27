# basic-app

Example application built on `alpha-core`. Demonstrates a multi-agent code review pipeline using all three workflow step types: sequential, parallel, and conditional.

## What it does

Takes a code snippet and runs it through a five-agent pipeline:

```text
CodeReview
   │
   ▼ parse (sequential) — understand the code structure
CodeSummary
   │
   ▼ analyze (parallel) — three agents run concurrently
   ├── security     → SecurityOut
   ├── performance  → PerformanceOut
   └── style        → StyleOut
        ↓ merged
   ReviewDraft
        │
        ▼ report (conditional on severity)
        ├── urgent   → ReviewReport   (high severity)
        └── standard → ReviewReport   (medium / low)
```

## Usage

### Run the code review workflow

```bash
uv run basic-app
```

Or directly:

```bash
uv run --package basic-app python -m basic_app.main
```

### Run the workspace demo

Demonstrates an agent with a local filesystem and sandbox — writes a Python file, runs it, and reports the output.

```bash
uv run workspace-demo
```

## Setup

Requires a `.env` file in this directory with API keys for your chosen model provider. Any provider supported by [litellm](https://github.com/BerriAI/litellm) works. The default model is `gemini/gemini-2.0-flash`:

```bash
cp .env.example .env
# add your API key to .env
```

## Agents

| Agent ID               | Role                                                         |
| ---------------------- | ------------------------------------------------------------ |
| `parser`               | Extracts purpose and design patterns from the code           |
| `security_reviewer`    | Identifies vulnerabilities and rates severity                |
| `performance_reviewer` | Flags algorithmic and memory inefficiencies                  |
| `style_reviewer`       | Reviews naming, readability, and best practices              |
| `report_writer`        | Synthesises findings into a structured report                |

## Structure

```text
basic-app/
├── src/basic_app/
│   └── main.py          # workflow definition and entry points
└── test_workspace/      # working directory used by the workspace demo
```

## See also

- [alpha-core](../../packages/core/README.md) — the framework this app is built on
- [Architecture](../../docs/architecture.md) — how workflows and agents work

Last updated: 2026-05-27
