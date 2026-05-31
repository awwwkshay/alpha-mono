# alpha-python

A Python framework for building and orchestrating AI agent workflows. Define agents, compose them into typed workflows with sequential, parallel, and conditional steps, and give them a sandboxed workspace to read/write files and run commands.

- [Architecture](docs/architecture.md) — how the pieces fit together
- [Development](docs/development.md) — setup and day-to-day commands

---

## Concepts

| Concept                         | What it is                                                    |
| ------------------------------- | ------------------------------------------------------------- |
| **`AlphaApp`**                  | Top-level container. Owns agents, workflows, and workspaces.  |
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
alpha-python/
├── packages/
│   └── core/               # alpha-core — the framework
│       └── src/alpha_core/
│           ├── domain/     # AlphaApp, Agent, Workflow, Workspace
│           ├── schemas/    # Config and context models
│           ├── contracts/  # FileSystem and Sandbox interfaces
│           └── types/
└── apps/
    └── basic-app/          # Example: multi-agent code reviewer
```

---

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Copy `.env.example` to `.env` and add your API keys (any provider supported by litellm).

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

**Defining a step:**

```python
async def parse_code(input: CodeReview, context: AppContext) -> CodeSummary:
    agent = context.agents["parser"]
    response = await agent.generate_async("Analyze this code...", context)
    return CodeSummary(...)
```

**Wiring it up:**

```python
app = AlphaApp(config=AppConfig(
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
uv run --package basic-app python -m basic_app.main
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
async with AlphaApp(config=config) as app:
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

# The LLM can now call the 'summarise' tool during generation
result = await agent.generate_async("Summarise this document...", context)
```

Multiple workflows and a workspace can be combined — the agent merges all tool schemas into a single list.

---

## Chat integrations (alpha-chat)

The `alpha-chat` package provides ready-to-use clients and FastAPI endpoints for connecting agents to Slack, Telegram, and GitHub.

```python
from alpha_chat import SlackClient, SlackAdapter, build_slack_router
from fastapi import FastAPI

slack_client = SlackClient(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])
adapter = SlackAdapter(agent=my_agent, context=app_context, slack_client=slack_client)

app = FastAPI()
app.include_router(build_slack_router(adapter), prefix="/slack")
```

The Slack router exposes three endpoints — `/slack/events` (Events API + URL verification), `/slack/commands` (slash commands), and `/slack/actions` (interactive components) — each with HMAC signature verification.

---

## Packages

| Package       | Description                                                    |
| ------------- | -------------------------------------------------------------- |
| `alpha-core`  | Core framework — agents, workflows, workspace                  |
| `alpha-chat`  | Chat integrations — Slack, Telegram, GitHub clients + webhooks |

Last updated: 2026-05-30
