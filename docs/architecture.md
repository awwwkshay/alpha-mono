# Architecture

## Overview

alpha-mono is structured around three layers:

```text
┌─────────────────────────────────────────────┐
│                   AlphaApp                  │  entry point, lifecycle
├──────────────┬──────────────────────────────┤
│   Workflows  │         Agents               │  orchestration & LLM calls
├──────────────┴──────────────────────────────┤
│                  Workspace                  │  filesystem + sandbox + skills
├─────────────────────────────────────────────┤
│        FileSystemContract / SandboxContract │  pluggable backends
└─────────────────────────────────────────────┘
```

Everything is configured via Pydantic models (`AppConfig`, `WorkflowConfig`, `AgentConfig`, `WorkspaceConfig`) and validated at construction time — schema mismatches are errors before any LLM call is made.

The codebase is split across three packages:

- **`alpha-core`** — schemas, contracts, and shared types (the interface layer)
- **`alpha-app`** — concrete implementations: `AlphaApp`, `Agent`, `Workflow`, `Workspace`, `Evals`
- **`alpha-chat`** — optional chat integrations: Slack, Telegram, GitHub clients, adapters, and routers

Use package-native imports at application boundaries:

```python
from alpha_core import AgentConfig, AppConfig, WorkflowConfig
from alpha_app import AlphaApp, Agent, Workflow
from alpha_chat import SlackChat, build_slack_router
```

---

## AlphaApp

`AlphaApp` is the top-level container. It owns and manages the lifecycle of agents, workflows, and workspaces.

**Construction (`__init__`)**

1. Loads env vars from the configured `.env` file.
2. Builds a global `Workspace` instance if `AppConfig.workspace` is set.
3. For each agent, uses its own `workspace` if configured, otherwise falls back to the global workspace.
4. Deduplicates workspace instances (so the global workspace is only set up once).
5. Instantiates `Agent` and `Workflow` objects.
6. Constructs `AppContext` — the read-only bag passed to every workflow step.
7. Sets up the FastAPI server and mounts any chat integrations declared in agent configs.

### Lifecycle

`AlphaApp` implements the async context manager protocol. `setup()` initialises each workspace (creates directories, opens connections). `teardown()` kills any running sandbox processes.

```python
async with AlphaApp(config=config) as app:
    ...  # workspaces ready here
# workspaces torn down on exit
```

When not using the context manager, call `setup()` / `teardown()` manually, or skip both if no workspace is configured.

---

## Workflows

A workflow is a typed pipeline of steps. Data flows through the steps in sequence: each step's output becomes the next step's input.

### Schema validation at config time

`WorkflowConfig` validates the entire step chain on construction:

- The workflow's `input_schema` must match the first step's `input_schema`.
- Each step's `output_schema` must match the next step's `input_schema`.
- The last step's `output_schema` must match the workflow's `output_schema`.

This means a misconfigured pipeline raises `WorkflowConfigError` at startup, not mid-run.

### Step types

**`WorkflowStep`** — the base unit. Wraps a single async function:

```python
async def my_step(input: MyInput, context: AppContext) -> MyOutput: ...
```

Input is validated against `input_schema` before the function is called. Output is validated against `output_schema` before being passed downstream.

**`ParallelWorkflowStep`** — fans the same input out to all branches concurrently (`asyncio.gather`), then merges the results into a single Pydantic model. Validated constraints:

- All branches must accept the same `input_schema` as the parallel step.
- Branch output fields must be non-overlapping.
- The parallel step's `output_schema` must be exactly the union of all branch output fields.

**`ConditionalWorkflowStep`** — calls a synchronous `condition` function to select a branch key, then executes that branch. All branches must share the same `input_schema` and `output_schema` as the step itself.

### Execution

`Workflow.execute(input_data, context)` iterates over steps in insertion order, threading `current_data` through each one. All schemas are validated at each boundary at runtime.

---

## Agents

`Agent` wraps a litellm model call. It supports three modes:

- `generate_async` — returns the full response as a string.
- `generate_structured_async` — returns a parsed Pydantic model instance (see below).
- `stream_async` — yields content tokens as an async iterator.

`generate_async` and `stream_async` implement the same **tool-use loop**:

```text
while iterations < MAX_TOOL_ITERATIONS:
    call LLM with messages + tools
    if no tool calls → return content
    for each tool call:
        dispatch to workspace tool or workflow
        append tool result to messages
raise RuntimeError  # iteration limit exceeded
```

### Structured output

`generate_structured_async(user_prompt, context, response_model)` makes a single LiteLLM call with `response_format=response_model` and returns a parsed instance of the given Pydantic model. No tool-call loop runs — this is a direct call intended for steps that need a typed response shape. The same agent can be called with different `response_model` types on each invocation:

```python
class Summary(BaseModel):
    title: str
    points: list[str]

result: Summary = await agent.generate_structured_async(prompt, context, Summary)
```

### Tool injection

Tools come from two sources that are merged at call time:

1. **Workspace tools** — if a `Workspace` is configured, its `get_tools()` method returns filesystem/sandbox/skill tool schemas.
2. **Workflow tools** — any `Workflow` instances passed via `AgentConfig(workflows={...})` are exposed as tools. The schema is auto-generated from the workflow's `input_schema` Pydantic model using `model_json_schema()`.

When the LLM calls a workflow tool, the agent validates the arguments against `workflow.config.input_schema`, calls `workflow.execute(input_data, context)`, and injects the serialised output back into the message loop. Workspace tools and workflow tools coexist — the agent dispatches to the correct handler based on the tool name.

If neither a workspace nor any workflows are configured, the agent receives no tools.

### Model selection

The `model` field in `AgentConfig` is passed directly to litellm, so any provider it supports works: `openai/gpt-4o`, `gemini/gemini-2.0-flash`, `anthropic/claude-opus-4-7`, etc.

---

## Workspace

`Workspace` composes three optional capabilities and exposes them to an agent as LLM tool schemas.

### Filesystem

Backed by a `FileSystemContract` implementation. The local implementation (`LocalFileSystem`) roots all paths under `base_path` and optionally enforces containment (no path traversal outside the root).

Tools exposed to the LLM:

| Tool               | Description                                    |
| ------------------ | ---------------------------------------------- |
| `read_file`        | Read file contents                             |
| `write_file`       | Create or overwrite a file                     |
| `edit_file`        | Replace a string in a file                     |
| `list_directory`   | List entries, with optional glob filter        |
| `delete_file`      | Delete a file                                  |
| `delete_directory` | Recursively delete a directory                 |
| `copy_file`        | Copy a file                                    |
| `move_file`        | Move or rename a file                          |
| `mkdir`            | Create a directory                             |
| `grep`             | Search for a regex pattern across files        |
| `stat`             | Return size, mtime, and type for a path        |

### Sandbox

Backed by a `SandboxContract` implementation. `LocalSandbox` runs subprocesses on the host machine with an optional isolation wrapper (`seatbelt` on macOS, `bwrap` on Linux). `E2BSandbox` provides cloud execution via the E2B platform.

Tools exposed to the LLM:

| Tool                 | Description                                          |
| -------------------- | ---------------------------------------------------- |
| `execute_command`    | Run a shell command (foreground or background)       |
| `get_process_output` | Read stdout/stderr from a background process         |
| `kill_process`       | Kill a process by PID                                |

### Skills

Skills are directories that contain a `skill.md` instructions file and optional supporting files. At workspace setup, all skill directories under the configured paths are loaded. Their instructions are injected into the agent's system prompt. Supporting files can be read via the `read_skill_file` tool.

```text
skills/
└── my_skill/
    ├── skill.md       ← injected into system prompt
    └── template.txt   ← readable via read_skill_file
```

---

## Extension points

### Custom filesystem backend

Subclass `FileSystemContract` and implement all abstract methods. Pass an instance via a custom config that `Workspace` recognises.

### Custom sandbox backend

Subclass `SandboxContract` and implement `setup`, `teardown`, `execute_command`, `get_process_output`, and `kill_process`.

---

## Chat integrations (alpha-chat)

The `packages/chat` package (`alpha_chat`) provides:

- **Clients** — thin async wrappers over official SDKs:
  - `SlackClient` — `send_message`, `set_status`, `react`, `open_modal`, `ack_slash_command`
  - `TelegramClient` — `send_message`, `set_webhook`, `delete_webhook`
  - `GithubClient` — `get_repo`, `create_issue`, `list_prs`

- **Endpoints** — FastAPI `APIRouter` builders. All Slack endpoints verify `X-Slack-Signature` HMAC before processing:
  - `build_slack_router(adapter)` — mounts `POST /events`, `POST /commands`, `POST /actions`
  - `build_telegram_router(adapter)` — mounts `POST /webhook`

- **Adapters** — bridge layer between platform events and an `Agent`:
  - `SlackAdapter(agent, context, slack_client)` — `handle_event`, `handle_command`, `handle_action`; maintains per-conversation history; shows typing status
  - `TelegramAdapter(agent, context, telegram_client)` — `handle_update`

- **`SlackChat`** — declarative integration. Add to `AgentConfig.chat` and `AlphaApp` mounts the router automatically.

**Wiring pattern (manual):**

```python
slack_client = SlackClient(token=..., signing_secret=...)
adapter = SlackAdapter(agent=my_agent, context=app_context, slack_client=slack_client)

app = FastAPI()
app.include_router(build_slack_router(adapter), prefix="/slack")
```

---

## Package structure

```text
packages/core/src/alpha_core/
├── schemas/
│   ├── app_config.py
│   ├── agent_config.py
│   ├── workflow_config.py       # WorkflowConfig + step configs + chain validation
│   ├── workspace_config.py
│   ├── filesystem_config.py
│   ├── sandbox_config.py
│   └── app_context.py
├── contracts/
│   └── workspace/
│       ├── file_system_contract.py
│       └── sandbox_contract.py
└── types/
    └── app_id.py

packages/app/src/alpha_app/
├── app/
│   └── app.py                   # AlphaApp
├── agent/
│   └── agent.py                 # Agent, tool-use loop, structured output
├── workflow/
│   └── workflow.py              # Workflow, step execution
├── workspace/
│   ├── workspace.py             # Workspace, tool dispatch, skills
│   ├── file_systems/
│   │   ├── local_file_system.py
│   │   └── s3_file_system.py
│   └── sandboxes/
│       ├── local_sandbox.py
│       └── e2b_sandbox.py
└── evals/
    ├── runner.py
    └── scorers/
        ├── answer_relevancy.py
        ├── bias.py
        ├── completeness.py
        ├── faithfulness.py
        ├── hallucination.py
        ├── keyword_coverage.py
        └── toxicity.py

packages/chat/src/alpha_chat/
├── clients/
│   ├── slack_client.py          # SlackClient
│   ├── telegram_client.py       # TelegramClient
│   └── github_client.py         # GithubClient
├── endpoints/
│   ├── slack/
│   │   ├── router.py            # build_slack_router, SlackChat
│   │   ├── events.py            # POST /events
│   │   ├── commands.py          # POST /commands
│   │   └── actions.py           # POST /actions
│   └── telegram/
│       └── webhook.py           # POST /webhook, build_telegram_router
├── adapters/
│   ├── slack_adapter.py         # SlackAdapter
│   └── telegram_adapter.py      # TelegramAdapter
└── schemas/
    ├── slack.py                 # SlackMessageEvent, SlackCommand, SlackAction
    └── telegram.py              # TelegramUpdate, TelegramMessage
```
