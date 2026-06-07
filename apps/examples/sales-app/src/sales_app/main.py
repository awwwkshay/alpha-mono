from __future__ import annotations

import asyncio
from pathlib import Path

from clay_app import ClayApp
from clay_core import AppConfig, ObservabilityConfig

from sales_app.workspaces.local_workspace import LOCAL_WORKSPACE


ENV_FILE = Path(__file__).parents[2] / ".env"

APP_CONFIG = AppConfig(
    name="sales-app",
    env_file=ENV_FILE,
    observability=ObservabilityConfig(endpoint="http://localhost:4317"),
    agents={},
    workflows={},
    workspace=LOCAL_WORKSPACE,
    debug=True,
)

APP = ClayApp(config=APP_CONFIG)


async def run_app() -> None:
    async with APP:
        print("Clay app initialized.")


def run() -> None:
    asyncio.run(run_app())
