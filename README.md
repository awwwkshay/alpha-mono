# clay-mono

A Python framework for building and orchestrating AI agent workflows. Define agents, compose them into typed workflows with sequential, parallel, and conditional steps, and give them a sandboxed workspace to read/write files and run commands.

- [Architecture](docs/architecture.md) — how the pieces fit together
- [Development](docs/development.md) — setup and day-to-day commands

---

## Concepts

| Concept                         | What it is                                                    |
| ------------------------------- | ------------------------------------------------------------- |
| **`ClayApp`**                  | Top-level container. Owns agents, workflows, and workspaces.  |
| **`Agent`**                     | Wraps an LLM via litellm. Supports tool use and streaming.    |
| **`Workflow`**                  | Typed pipeline — each step's output feeds the next step.      |
| **`WorkflowStep`**              | Single async step: `(InputModel, AppContext) → OutputModel`.  |
| **`ParallelWorkflowStep`**      | Runs branches concurrently with the same input, merges output.|
| **`ConditionalWorkflowStep`**   | Routes to one branch based on a condition function.           |
| **`Workspace`**                 | Gives an agent a filesystem and sandbox to run commands in.   |

Schemas are [Pydantic](https://docs.pydantic.dev/) models — step inputs and outputs are validated at runtime.

---

## Repo layout

```text
clay-mono/
├── packages/
│   ├── core/               # clay-core — schemas, contracts, interfaces
│   ├── app/                # clay-app  — Agent, ClayApp, Workflow, Workspace, Evals
│   └── chat/               # clay-chat — Slack, Telegram, GitHub integrations
└── apps/
    ├── cli/               # clay-cli — command-line app scaffolding
    ├── studio-server/     # clay-studio-server — local Studio API and SPA server
    └── examples/
        ├── basic-app/      # Example: multi-agent code reviewer
        └── personal-agent/ # Example: Slack-connected personal assistant
```

---

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-packages
```

Copy `.env.example` to `.env` in the relevant app directory and add your API keys (any provider supported by litellm).

---

## CLI

Initialize a new Clay app:

```bash
uv run clay init my-app
```

The command creates a minimal runnable app with `pyproject.toml`, `README.md`,
`clay.yaml`, `.env.example`, and a `src/<module>/main.py` entry point.

Start the local Studio UI from a Clay app directory:

```bash
uv run clay studio
```

---

## Example

The `basic-app` is a multi-agent code reviewer that shows all three step types:

```text
CodeReview
   │
   ▼ parse (sequential)
CodeSummary
   │
   ▼ analyze (parallel)
   ├── security  → SecurityOut
   ├── performance → PerformanceOut
   └── style → StyleOut
        ↓ merged
   ReviewDraft
        │
        ▼ report (conditional on severity)
        ├── urgent → ReviewReport
        └── standard → ReviewReport
```

**Import guide:**

```python
# Define configuration, schemas, contracts, and tool abstractions.
from clay_core import AgentConfig, AppConfig, AppContext, WorkflowConfig

# Run agents, apps, workflows, workspaces, and eval implementations.
from clay_app import Agent, ClayApp, Workflow

# Add optional chat integrations.
from clay_chat import SlackChat, SlackClient, build_slack_router
```

**Defining a step:**

```python
async def parse_code(input: CodeReview, context: AppContext) -> CodeSummary:
    agent = context.agents["parser"]
    response = await agent.generate_async("Analyze this code...", context)
    return CodeSummary(...)
```

**Wiring it up:**

```python
app = ClayApp(config=AppConfig(
    name="code-reviewer",
    agents={"parser": AgentConfig(name="Parser", model="gemini/gemini-2.0-flash", ...)},
    workflows={
        "review": WorkflowConfig.create(
            input_schema=CodeReview,
            output_schema=ReviewReport,
            steps={
                "parse": WorkflowStepConfig.create(execute=parse_code, ...),
                "analyze": ParallelWorkflowStepConfig.create(branches={...}),
                "report": ConditionalWorkflowStepConfig.create(condition=route_by_severity, branches={...}),
            },
        )
    },
))

result = await app.execute_workflow("review", {"language": "Python", "code": "..."})
```

Run it:

```bash
uv run basic-app
```

---

## Workspace

Give an agent a local filesystem and sandbox:

```python
AppConfig(
    workspace=WorkspaceConfig(
        filesystem=LocalFilesystemConfig(base_path=Path("./workspace")),
        sandbox=LocalSandboxConfig(working_directory=Path("./workspace"), timeout=30),
    )
)
```

The agent gets tools to read/write files, run shell commands, list directories, and more. Use as a context manager to ensure setup/teardown:

```python
async with ClayApp(config=config) as app:
    result = await app.agents["coder"].generate_async("Write fib.py and run it.", app.context)
```

---

## Workflows as Agent Tools

A `Workflow` can be given directly to an `Agent` as a callable tool. The agent's LLM can then invoke the workflow by name; the tool schema is auto-generated from the workflow's `input_schema` Pydantic model.

```python
summarise = Workflow.create(config=WorkflowConfig(...))

agent = Agent(
    config=AgentConfig(name="assistant", model="gpt-4o", ...),
    workflows={"summarise": summarise},
)

result = await agent.generate_async("Summarise this document...", context)
```

Multiple workflows and a workspace can be combined — the agent merges all tool schemas into a single list.

---

## Chat integrations (clay-chat)

The `clay-chat` package provides ready-to-use clients and FastAPI endpoints for connecting agents to Slack, Telegram, and GitHub.

Declare chat integrations directly on an `AgentConfig`:

```python
from clay_core import AgentConfig
from clay_chat import SlackChat

AgentConfig(
    name="Jarvis",
    model="gemini/gemini-flash-latest",
    chat=[SlackChat()],
)
```

`ClayApp` automatically mounts the required endpoints (e.g. `/events`, `/commands`, `/actions` for Slack) when a chat integration is declared.

Or wire it manually:

```python
from clay_chat import SlackClient, SlackAdapter, build_slack_router
from fastapi import FastAPI

slack_client = SlackClient(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])
adapter = SlackAdapter(agent=my_agent, context=app_context, slack_client=slack_client)

app = FastAPI()
app.include_router(build_slack_router(adapter), prefix="/slack")
```

The Slack router exposes `/events` (Events API + URL verification), `/commands` (slash commands), and `/actions` (interactive components), each with HMAC signature verification.

---

## Packages

| Package       | Description                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| `clay-core`  | Schemas, contracts, and interfaces — the framework's type layer              |
| `clay-app`   | Runtime implementations — `Agent`, `ClayApp`, `Workflow`, `Workspace`, `Evals` |
| `clay-chat`  | Chat integrations — Slack, Telegram, GitHub clients, adapters, and endpoints |
| `clay-cli`   | CLI commands for initializing Clay apps                                      |
| `clay-studio-server` | Local FastAPI server and embedded SPA assets for Clay Studio         |
