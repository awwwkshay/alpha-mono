# alpha-app

Concrete implementations for the alpha-mono framework. Provides `Agent`, `AlphaApp`, `Workflow`, `Workspace`, and a suite of LLM-based eval scorers, all built on the schemas and contracts defined in `alpha-core`.

## Installation

This package is consumed as a workspace dependency. From the repo root:

```bash
uv sync --all-packages
```

To build a distributable wheel:

```bash
uv build --package alpha-app
```

## What's in this package

### Core classes

| Class       | Purpose                                                                 |
| ----------- | ----------------------------------------------------------------------- |
| `AlphaApp`  | Top-level container — owns agents, workflows, workspaces, and server    |
| `Agent`     | LLM wrapper with tool-use loop, structured output, and streaming        |
| `Workflow`  | Typed step pipeline executor                                            |
| `Workspace` | Composes filesystem, sandbox, and skills; exposes tools to the LLM     |

### Workspace backends

| Class              | Config                  | Description                                  |
| ------------------ | ----------------------- | -------------------------------------------- |
| `LocalFileSystem`  | `LocalFilesystemConfig` | Local disk, paths rooted under `base_path`   |
| `S3FileSystem`     | `S3FilesystemConfig`    | S3 bucket filesystem                         |
| `LocalSandbox`     | `LocalSandboxConfig`    | Local subprocess with optional `seatbelt`/`bwrap` isolation |
| `E2BSandbox`       | `E2BSandboxConfig`      | E2B cloud sandbox                            |

### Eval scorers

Run LLM-graded evaluations on agent outputs:

| Scorer                    | What it measures                                    |
| ------------------------- | --------------------------------------------------- |
| `AnswerRelevancyScorer`   | How relevant the response is to the question        |
| `BiasScorer`              | Presence of bias in the response                    |
| `CompletenessScorer`      | Coverage of required information                    |
| `FaithfulnessScorer`      | Factual consistency with provided context           |
| `HallucinationScorer`     | Fabricated or unsupported claims                    |
| `KeywordCoverageScorer`   | Coverage of expected keywords                       |
| `ToxicityScorer`          | Harmful or toxic content                            |

```python
from alpha_app import run_evals, EvalCase, AnswerRelevancyScorer

results = await run_evals(
    agent=agent,
    context=context,
    cases=[EvalCase(input="What is X?", expected="X is ...")],
    scorers=[AnswerRelevancyScorer()],
)
```

### Chat integrations

Chat integrations live in `alpha-chat`. Import them from there so package ownership stays clear:

```python
from alpha_chat import SlackChat, SlackClient, SlackAdapter, build_slack_router
```

## Quick start

```python
from alpha_app import AlphaApp
from alpha_core import AgentConfig, AppConfig, WorkflowConfig, WorkflowStepConfig

async def my_step(input: MyInput, context: AppContext) -> MyOutput:
    agent = context.agents["my_agent"]
    result = await agent.generate_async("Do something with this...", context)
    return MyOutput(...)

app = AlphaApp(config=AppConfig(
    name="my-app",
    agents={"my_agent": AgentConfig(name="MyAgent", model="gemini/gemini-2.0-flash")},
    workflows={
        "my_workflow": WorkflowConfig.create(
            input_schema=MyInput,
            output_schema=MyOutput,
            steps={"step1": WorkflowStepConfig.create(execute=my_step, ...)},
        )
    },
))

result = await app.execute_workflow("my_workflow", {"field": "value"})
```

## See also

- [alpha-core](../core/README.md) — schemas and contracts this package implements
- [alpha-chat](../chat/README.md) — chat integration details
- [Architecture](../../docs/architecture.md) — detailed design of all components
