from __future__ import annotations

import asyncio
from pathlib import Path
from textwrap import dedent

from alpha_core.domain.app.app import AlphaApp
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.filesystem_config import LocalFilesystemConfig
from alpha_core.schemas.sandbox_config import LocalSandboxConfig
from alpha_core.schemas.workspace_config import WorkspaceConfig

from basic_app.agents import AGENTS
from basic_app.evals import print_eval_results, run_parser_evals
from basic_app.workflows import REVIEW_WORKFLOW

ENV_FILE = Path(__file__).parents[2] / ".env"
WORKSPACE_DIR = Path(__file__).parents[2] / "test_workspace"


async def run_review() -> None:
    config = AppConfig(
        name="code-reviewer",
        env_file=ENV_FILE,
        agents=AGENTS,
        workflows={"review": REVIEW_WORKFLOW},
    )

    app = AlphaApp(config=config)
    result = await app.execute_workflow(
        "review",
        {
            "language": "Python",
            "code": dedent("""
                from collections import Counter
                from pathlib import Path

                def count_chars(filename: str) -> list[tuple[str, int]]:
                    data = Path(filename).read_text()
                    return Counter(data).most_common()
            """).strip(),
        },
    )

    print(f"\nVerdict: {result['verdict']}")
    print("\nPriority Issues:")
    for issue in result["priority_issues"]:
        print(f"  • {issue}")
    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  • {rec}")


async def run_workspace() -> None:
    WORKSPACE_DIR.mkdir(exist_ok=True)
    print(f"Workspace directory: {WORKSPACE_DIR}\n")

    config = AppConfig(
        name="workspace-demo",
        env_file=ENV_FILE,
        agents={
            "coder": AgentConfig(
                name="Coder",
                system_prompt=(
                    "You are a Python developer working inside a sandboxed workspace. "
                    "Use the available tools to write files, run commands, and verify results. "
                    "Always check command output before reporting success."
                ),
                model="gemini/gemini-2.0-flash",
            )
        },
        workspace=WorkspaceConfig(
            name="sandbox",
            filesystem=LocalFilesystemConfig(base_path=WORKSPACE_DIR),
            sandbox=LocalSandboxConfig(
                working_directory=WORKSPACE_DIR,
                timeout=15,
            ),
        ),
    )

    async with AlphaApp(config=config) as app:
        result = await app.agents["coder"].generate_async(
            dedent("""
                Do the following steps in order:
                1. Write a file called `fib.py` that prints the first 10 Fibonacci numbers.
                2. Run `python fib.py` and capture the output.
                3. Reply with the exact output the script produced.
            """),
            app.context,
        )

    print("=== Agent result ===")
    print(result)
    print(f"\n=== Files in {WORKSPACE_DIR} ===")
    for f in sorted(WORKSPACE_DIR.iterdir()):
        print(f"\n--- {f.name} ---")
        print(f.read_text())


async def run_evals_demo() -> None:
    config = AppConfig(
        name="eval-demo",
        env_file=ENV_FILE,
        agents={"parser": AGENTS["parser"]},
    )

    app = AlphaApp(config=config)
    results = await run_parser_evals(app.agents["parser"], app.context)
    print_eval_results(results)


def run() -> None:
    asyncio.run(run_review())


def run_workspace_demo() -> None:
    asyncio.run(run_workspace())


def run_eval_demo() -> None:
    asyncio.run(run_evals_demo())
