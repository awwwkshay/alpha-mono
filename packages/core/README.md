# alpha-core

Core framework package for alpha-mono. Provides the building blocks for defining and running AI agent workflows: agents, workflows, workspaces, config schemas, and pluggable filesystem/sandbox backends.

## Installation

This package is consumed as a workspace dependency. From the repo root:

```bash
uv sync
```

To build a distributable wheel:

```bash
uv build --package alpha-core
```

## What's in this package

### Domain

| Module                        | What it provides                                                              |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `alpha_core.domain.app`       | `AlphaApp` — top-level container, owns agents, workflows, workspaces          |
| `alpha_core.domain.agent`     | `Agent` — wraps a litellm model call with a tool-use loop                     |
| `alpha_core.domain.workflow`  | `Workflow`, `WorkflowStep`, `ParallelWorkflowStep`, `ConditionalWorkflowStep` |
| `alpha_core.domain.workspace` | `Workspace` — composes filesystem, sandbox, and skills                        |

### Schemas (config models)

| Schema                          | Purpose                                                |
| ------------------------------- | ------------------------------------------------------ |
| `AppConfig`                     | Top-level app configuration                            |
| `AgentConfig`                   | Model, system prompt, and optional per-agent workspace |
| `WorkflowConfig`                | Typed step pipeline with chain validation              |
| `WorkflowStepConfig`            | Single async step                                      |
| `ParallelWorkflowStepConfig`    | Fan-out to concurrent branches, merge outputs          |
| `ConditionalWorkflowStepConfig` | Route to one branch based on a condition               |
| `WorkspaceConfig`               | Filesystem + sandbox + skills config                   |
| `LocalFilesystemConfig`         | Local disk filesystem backend                          |
| `S3FilesystemConfig`            | S3 filesystem backend (stub)                           |
| `LocalSandboxConfig`            | Local subprocess sandbox                               |
| `E2BSandboxConfig`              | E2B cloud sandbox (stub)                               |

### Contracts (extension interfaces)

| Contract             | Implement to add a custom backend   |
| -------------------- | ----------------------------------- |
| `FileSystemContract` | Pluggable filesystem backend        |
| `SandboxContract`    | Pluggable command execution backend |

## Dependencies

| Package         | Purpose                             |
| --------------- | ----------------------------------- |
| `litellm`       | Model-agnostic LLM calls            |
| `pydantic`      | Config validation and schema models |
| `python-dotenv` | `.env` file loading                 |

## See also

- [Architecture](../../docs/architecture.md) — detailed design of all components
- [Development](../../docs/development.md) — setup and tooling

Last updated: 2026-05-27
