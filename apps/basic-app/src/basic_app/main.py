from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from textwrap import dedent

from alpha_core.domain.app.app import AlphaApp
from alpha_core.schemas.agent_config import AgentConfig
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.filesystem_config import LocalFilesystemConfig
from alpha_core.schemas.sandbox_config import LocalSandboxConfig
from alpha_core.schemas.workspace_config import WorkspaceConfig
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from basic_app.agents import AGENTS
from basic_app.doc_gen import DOC_GEN_WORKFLOW, create_doc_gen_agents
from basic_app.evals import print_eval_results, run_parser_evals
from basic_app.workflows import REVIEW_WORKFLOW

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

resource = Resource(attributes={"service.name": "alpha-basic-app"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

ENV_FILE = Path(__file__).parents[2] / ".env"
WORKSPACE_DIR = Path(__file__).parents[2] / "test_workspace"
_SOURCE_DIR = Path(__file__).parent

APP_CONFIG = AppConfig(
    name="basic-app",
    env_file=ENV_FILE,
    agents={
        **AGENTS,
        **create_doc_gen_agents(_SOURCE_DIR),
        "coder": AgentConfig(
            name="Coder",
            system_prompt=(
                "You are a Python developer working inside a sandboxed workspace. "
                "Use the available tools to write files, run commands, and verify results. "
                "Always check command output before reporting success."
            ),
            model="gemini/gemini-2.0-flash",
            workspace=WorkspaceConfig(
                name="sandbox",
                filesystem=LocalFilesystemConfig(base_path=WORKSPACE_DIR),
                sandbox=LocalSandboxConfig(
                    working_directory=WORKSPACE_DIR,
                    timeout=15,
                ),
            ),
        ),
    },
    workflows={
        "review": REVIEW_WORKFLOW,
        "doc_gen": DOC_GEN_WORKFLOW,
    },
    debug=True,
)

APP = AlphaApp(config=APP_CONFIG)


async def run_review() -> None:
    result = await APP.execute_workflow(
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

    print(f"\nVerdict: {result.verdict}")
    print("\nPriority Issues:")
    for issue in result.priority_issues:
        print(f"  • {issue}")
    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f"  • {rec}")


async def run_evals_demo() -> None:
    results = await run_parser_evals(APP.agents["parser"], APP.context)
    print_eval_results(results)


async def run_doc_gen() -> None:
    async with APP:
        result = await APP.execute_workflow(
            "doc_gen",
            {"file_path": "schemas.py"},
        )

    print(f"\n=== Documentation for {result.file_path} ===\n")
    print(result.documentation)


def run() -> None:
    asyncio.run(run_review())


def run_eval_demo() -> None:
    asyncio.run(run_evals_demo())


def run_doc_gen_demo() -> None:
    asyncio.run(run_doc_gen())
