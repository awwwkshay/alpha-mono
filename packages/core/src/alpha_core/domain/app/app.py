from __future__ import annotations

from typing import Any
from dotenv import load_dotenv
from opentelemetry import trace

from alpha_core.domain.agent.agent import Agent
from alpha_core.domain.workflow.workflow import Workflow
from alpha_core.domain.workspace.workspace import Workspace
from alpha_core.log import logger
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext
from alpha_core.types.app_id import AppId


class AlphaApp:
    config: AppConfig
    context: AppContext
    agents: dict[AppId, Agent]
    workflows: dict[AppId, Workflow]

    def __init__(self, *, config: AppConfig) -> None:
        import logging

        if config.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        load_dotenv(dotenv_path=config.env_file)
        self.config = config

        # Build workspace instances — deduplicate so the global workspace is shared.
        global_workspace = Workspace(config.workspace) if config.workspace else None

        agent_workspaces: dict[AppId, Workspace | None] = {}
        for agent_id, agent_cfg in config.agents.items():
            if agent_cfg.workspace:
                agent_workspaces[agent_id] = Workspace(agent_cfg.workspace)
            else:
                agent_workspaces[agent_id] = global_workspace

        # Collect unique Workspace instances for lifecycle management.
        self._workspaces: set[Workspace] = {
            w for w in agent_workspaces.values() if w is not None
        }
        if global_workspace:
            self._workspaces.add(global_workspace)

        self.agents = {
            agent_id: Agent(config=agent_cfg, workspace=agent_workspaces[agent_id])
            for agent_id, agent_cfg in config.agents.items()
        }
        self.workflows = {
            app_id: Workflow(config=workflow_config)
            for app_id, workflow_config in config.workflows.items()
        }
        self.context = AppContext(
            config=self.config,
            workflows=self.workflows,
            agents=self.agents,
        )

    async def setup(self) -> None:
        logger.debug(
            f"Setting up app '{self.config.name}' (workspaces={len(self._workspaces)})"
        )
        for workspace in self._workspaces:
            await workspace.setup()
        logger.info(f"App '{self.config.name}' setup complete")

    async def teardown(self) -> None:
        logger.debug(f"Tearing down app '{self.config.name}'")
        for workspace in self._workspaces:
            await workspace.teardown()
        logger.info(f"App '{self.config.name}' teardown complete")

    async def __aenter__(self) -> AlphaApp:
        await self.setup()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.teardown()

    async def execute_workflow(self, workflow_id: AppId, input_data: Any) -> Any:
        tracer = trace.get_tracer(__name__)
        logger.info(f"Executing workflow '{workflow_id}' in app '{self.config.name}'")
        with tracer.start_as_current_span(
            f"AlphaApp.execute_workflow/{workflow_id}",
            attributes={"workflow_id": workflow_id},
        ):
            result = await self.workflows[workflow_id].execute(input_data, self.context)
            logger.info(f"Completed workflow '{workflow_id}'")
            return result


__all__ = ["AlphaApp"]
