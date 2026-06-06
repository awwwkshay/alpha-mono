# basic-app

Example application built on `clay-app`. Demonstrates a multi-agent code review pipeline using all three workflow step types — sequential, parallel, and conditional — plus an agent with a sandboxed workspace and a documentation generation workflow.

## What it does

### Code review workflow

Takes a code snippet and routes it through a five-agent pipeline:

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

### Doc-gen workflow

Reads a source file from the workspace filesystem and generates structured documentation for it using a two-step pipeline (read → document).

### Eval demo

Runs LLM-graded evaluations on the `parser` agent using a suite of test cases and scorers.

## Usage

```bash
# Run the code review workflow
uv run basic-app

# Run the eval demo
uv run eval-demo

# Run the documentation generation workflow
uv run doc-gen
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
| `coder`                | Writes and runs Python in a sandboxed local workspace        |

## Structure

```text
basic-app/
├── src/basic_app/
│   ├── main.py          # AppConfig, entry points
│   ├── schemas.py       # Pydantic models for the review pipeline
│   ├── agents.py        # Agent configs
│   ├── workflows.py     # Workflow config
│   ├── steps.py         # Step implementations
│   ├── evals.py         # Eval cases and runner
│   └── doc_gen/         # Documentation generation subapp
│       ├── agents.py
│       ├── workflows.py
│       ├── steps.py
│       └── schemas.py
└── test_workspace/      # Working directory used by the coder agent
```

## See also

- [clay-app](../../../packages/app/README.md) — the framework this app is built on
- [Architecture](../../../docs/architecture.md) — how workflows and agents work
