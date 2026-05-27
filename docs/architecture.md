# Architecture

## Overview

alpha-python is structured around three layers:

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

**`ParallelWorkflowStep`** — fans the same input out to all branches concurrently (`asyncio.gather`), then merges the results into a single dict. Validated constraints:

- All branches must accept the same `input_schema` as the parallel step.
- Branch output fields must be non-overlapping.
- The parallel step's `output_schema` must be exactly the union of all branch output fields.

**`ConditionalWorkflowStep`** — calls a synchronous `condition` function to select a branch key, then executes that branch. All branches must share the same `input_schema` and `output_schema` as the step itself.

### Execution

`Workflow.execute(input_data, context)` iterates over steps in insertion order, threading `current_data` through each one. All schemas are validated at each boundary at runtime.

---

## Agents

`Agent` wraps a litellm model call. It supports two modes:

- `generate_async` — returns the full response as a string.
- `stream_async` — yields content tokens as an async iterator.

Both modes implement the same **tool-use loop**:

```text
while iterations < MAX_TOOL_ITERATIONS:
    call LLM with messages + tools
    if no tool calls → return content
    for each tool call:
        execute via workspace.execute_tool(name, args)
        append tool result to messages
raise RuntimeError  # iteration limit exceeded
```

The `context: AppContext` parameter is available for future use (e.g. accessing other agents or workflows from within a step).

### Tool injection

Tools are provided by the agent's `Workspace`. If no workspace is configured, the agent receives no tools and the LLM cannot call any. The workspace's `get_tools()` method returns the litellm-compatible tool schema list.

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

Backed by a `SandboxContract` implementation. `LocalSandbox` runs subprocesses on the host machine with an optional isolation wrapper (`seatbelt` on macOS, `bwrap` on Linux). `E2BSandbox` is a stub for cloud execution (not yet implemented).

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

Subclass `FileSystemContract` and implement all abstract methods. Pass an instance via a custom config:

```python
class MyFilesystemConfig(FilesystemConfig):
    ...

# In workspace.py _build_filesystem, add handling for MyFilesystemConfig
```

### Custom sandbox backend

Subclass `SandboxContract` and implement `setup`, `teardown`, `execute_command`, `get_process_output`, and `kill_process`.

---

## Package structure

```text
packages/core/src/alpha_core/
├── domain/
│   ├── app/
│   │   └── app.py               # AlphaApp
│   ├── agent/
│   │   ├── agent.py             # Agent, tool-use loop
│   │   └── tool/agent_tool.py
│   ├── workflow/
│   │   └── workflow.py          # Workflow, WorkflowStep, Parallel, Conditional
│   └── workspace/
│       ├── workspace.py         # Workspace, tool dispatch, skills
│       ├── file_systems/
│       │   ├── local_file_system.py
│       │   └── s3_file_system.py   # stub
│       └── sandboxes/
│           ├── local_sandbox.py
│           └── e2b_sandbox.py      # stub
├── schemas/
│   ├── app_config.py
│   ├── agent_config.py
│   ├── workflow_config.py       # WorkflowConfig + step configs + validation
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
```

Last updated: 2026-05-27
