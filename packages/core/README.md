# clay-core

The type layer for the clay-mono framework. Provides schemas (Pydantic config models), contracts (abstract interfaces for pluggable backends), and shared types used across all packages.

> **Note:** `clay-core` defines the interfaces. Concrete implementations of `Agent`, `ClayApp`, `Workflow`, and `Workspace` live in [`clay-app`](../app/README.md).

## Installation

Install from PyPI:

```bash
pip install clay-core
```

For local development in this repo:

```bash
uv sync --all-packages
```

To build a distributable wheel:

```bash
uv build --package clay-core
```

## What's in this package

### Schemas (config models)

| Schema                          | Purpose                                                |
| ------------------------------- | ------------------------------------------------------ |
| `AppConfig`                     | Top-level app configuration                            |
| `AgentConfig`                   | Model, system prompt, tools, workflows, chat integrations, and optional per-agent workspace |
| `WorkflowConfig`                | Typed step pipeline with chain validation at construction time |
| `WorkflowStepConfig`            | Single async step                                      |
| `ParallelWorkflowStepConfig`    | Fan-out to concurrent branches, merge outputs          |
| `ConditionalWorkflowStepConfig` | Route to one branch based on a condition               |
| `WorkspaceConfig`               | Filesystem + sandbox + skills config                   |
| `LocalFilesystemConfig`         | Local disk filesystem backend                          |
| `S3FilesystemConfig`            | S3 filesystem backend                                  |
| `LocalSandboxConfig`            | Local subprocess sandbox                               |
| `E2BSandboxConfig`              | E2B cloud sandbox                                      |
| `ServerConfig`                  | Host and port for the built-in FastAPI server          |
| `AppContext`                    | Read-only context bag passed to every workflow step    |

### Contracts (extension interfaces)

| Contract             | Implement to add a custom backend       |
| -------------------- | --------------------------------------- |
| `FileSystemContract` | Pluggable filesystem backend            |
| `SandboxContract`    | Pluggable command execution backend     |
| `Scorer`             | Custom eval scorer                      |

### Other exports

| Export       | Purpose                                              |
| ------------ | ---------------------------------------------------- |
| `AgentTool`  | Wrap a Python function as an LLM-callable tool       |
| `logger`     | Shared logger (`clay_core`)                         |

## Dependencies

| Package         | Purpose                             |
| --------------- | ----------------------------------- |
| `litellm`       | Model-agnostic LLM calls            |
| `pydantic`      | Config validation and schema models |
| `python-dotenv` | `.env` file loading                 |

## See also

- [clay-app](../app/README.md) — concrete implementations built on these interfaces
- [Architecture](../../docs/architecture.md) — detailed design of all components
- [Development](../../docs/development.md) — setup and tooling
