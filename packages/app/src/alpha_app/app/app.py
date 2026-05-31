from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from opentelemetry import trace

from alpha_app.agent.agent import Agent
from alpha_app.server.server import Server
from alpha_app.workflow.workflow import Workflow
from alpha_app.workspace.workspace import Workspace
from alpha_core.log import logger
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext
from alpha_core.schemas.server_config import ServerConfig
from alpha_core.types.app_id import AppId

if TYPE_CHECKING:
    from fastapi import APIRouter


class AlphaApp:
    config: AppConfig
    context: AppContext
    agents: dict[AppId, Agent]
    workflows: dict[AppId, Workflow]
    server: Server

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
            agent_id: Agent(config=agent_cfg)
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
        server_cfg = config.server or ServerConfig()
        if not server_cfg.title:
            server_cfg = server_cfg.model_copy(update={"title": config.name})
        self.server = Server(config=server_cfg)

        for agent_app_id, agent_config in self.config.agents.items():
            for chat_integration in agent_config.chat:
                chat_integration.mount(self, self.agents[agent_app_id])

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

    def mount_router(self, router: APIRouter) -> None:
        self.server.mount_router(router)

    def serve(self) -> None:
        logger.info(f"Starting server for '{self.config.name}'")
        self.server.serve()

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
