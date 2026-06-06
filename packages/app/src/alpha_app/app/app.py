from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from alpha_app.constants.otel_constants import (
    APP_NAME,
    APP_WORKFLOW_ID,
    ERROR_MESSAGE,
    ERROR_TYPE,
    SPAN_APP_EXECUTE_WORKFLOW,
)

from alpha_app.agent.agent import Agent
from alpha_app.log import logger
from alpha_app.server.server import Server
from alpha_app.workflow.workflow import Workflow
from alpha_app.workspace.workspace import Workspace
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext
from alpha_core.schemas.server_config import ServerConfig
from alpha_core.types.app_id import AppId

if TYPE_CHECKING:
    from fastapi import APIRouter


_owned_tracer_provider: TracerProvider | None = None
_owned_tracer_provider_refcount = 0


class AlphaApp:
    config: AppConfig
    context: AppContext
    agents: dict[AppId, Agent]
    workflows: dict[AppId, Workflow]
    server: Server
    _tracer_provider: TracerProvider | None

    def __init__(self, *, config: AppConfig) -> None:
        if config.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        load_dotenv(dotenv_path=config.env_file)
        self.config = config
        self._tracer_provider = None
        self._setup_tracing(config)

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
        self._agent_workspaces = agent_workspaces

        self.agents = {
            agent_id: Agent(config=agent_cfg)
            for agent_id, agent_cfg in config.agents.items()
        }
        self.workflows = {
            app_id: Workflow(config=workflow_config)
            for app_id, workflow_config in config.workflows.items()
        }
        self._agent_contexts = {
            agent_id: AppContext(
                config=self.config,
                workflows=self.workflows,
                agents=self.agents,
                workspace=workspace,
            )
            for agent_id, workspace in agent_workspaces.items()
        }
        for agent_context in self._agent_contexts.values():
            agent_context.agent_contexts = self._agent_contexts
        self.context = AppContext(
            config=self.config,
            workflows=self.workflows,
            agents=self.agents,
            workspace=global_workspace,
            agent_contexts=self._agent_contexts,
        )
        server_cfg = config.server or ServerConfig()
        if not server_cfg.title:
            server_cfg = server_cfg.model_copy(update={"title": config.name})
        self.server = Server(config=server_cfg)
        self.server.add_startup(self.setup)
        self.server.add_teardown(self.teardown)

        for agent_app_id, agent_config in self.config.agents.items():
            for chat_integration in agent_config.chat:
                chat_integration.mount(self, self.agents[agent_app_id], agent_app_id)

    def _setup_tracing(self, config: AppConfig) -> None:
        global _owned_tracer_provider, _owned_tracer_provider_refcount

        obs = config.observability
        if obs is None or not obs.enabled:
            return
        if _owned_tracer_provider is not None:
            _owned_tracer_provider_refcount += 1
            self._tracer_provider = _owned_tracer_provider
            existing_service = (
                _owned_tracer_provider.resource.attributes.get("service.name", "")
            )
            new_service = obs.service_name or config.name
            if existing_service and existing_service != new_service:
                logger.warning(
                    f"Tracing already configured for service='{existing_service}'; "
                    f"app '{config.name}' (service='{new_service}') will share that "
                    "provider — its spans will be attributed to the first service name. "
                    "Create apps with the same service_name or avoid multiple AlphaApp "
                    "instances in the same process to prevent this."
                )
            else:
                logger.debug("Tracing already configured; reusing global tracer provider")
            return

        service_name = obs.service_name or config.name
        resource = Resource(attributes={"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=obs.endpoint, insecure=obs.insecure)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _owned_tracer_provider = provider
        _owned_tracer_provider_refcount = 1
        self._tracer_provider = provider
        logger.debug(
            f"Tracing enabled: service='{service_name}' endpoint='{obs.endpoint}'"
        )

    async def setup(self) -> None:
        logger.debug(
            f"Setting up app '{self.config.name}' (workspaces={len(self._workspaces)})"
        )
        for workspace in self._workspaces:
            await workspace.setup()
        for agent_config in self.config.agents.values():
            for chat_integration in agent_config.chat:
                await chat_integration.setup()
        logger.info(f"App '{self.config.name}' setup complete")

    async def teardown(self) -> None:
        global _owned_tracer_provider, _owned_tracer_provider_refcount

        logger.debug(f"Tearing down app '{self.config.name}'")
        for workspace in self._workspaces:
            await workspace.teardown()
        if self._tracer_provider is not None:
            await asyncio.to_thread(self._tracer_provider.force_flush)
            if self._tracer_provider is _owned_tracer_provider:
                _owned_tracer_provider_refcount = max(
                    0, _owned_tracer_provider_refcount - 1
                )
                if _owned_tracer_provider_refcount == 0:
                    await asyncio.to_thread(self._tracer_provider.shutdown)
                    _owned_tracer_provider = None
                    logger.debug("Tracer provider flushed and shut down")
                else:
                    logger.debug("Tracer provider flushed")
            else:
                logger.debug("Tracer provider flushed")
            self._tracer_provider = None
        logger.info(f"App '{self.config.name}' teardown complete")

    async def __aenter__(self) -> AlphaApp:
        await self.setup()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.teardown()

    def mount_router(self, router: APIRouter, prefix: str = "") -> None:
        self.server.mount_router(router, prefix=prefix)

    def get_agent_context(self, agent_id: AppId) -> AppContext:
        try:
            return self._agent_contexts[agent_id]
        except KeyError:
            known = list(self._agent_contexts.keys())
            raise KeyError(
                f"No agent context for {agent_id!r}. Known agents: {known}"
            ) from None

    def serve(self) -> None:
        logger.info(f"Starting server for '{self.config.name}'")
        self.server.serve()

    async def execute_workflow(self, workflow_id: AppId, input_data: Any) -> Any:
        _tracer = trace.get_tracer(__name__)
        logger.info(f"Executing workflow '{workflow_id}' in app '{self.config.name}'")
        with _tracer.start_as_current_span(
            f"{SPAN_APP_EXECUTE_WORKFLOW}/{workflow_id}",
            attributes={
                APP_NAME: self.config.name,
                APP_WORKFLOW_ID: workflow_id,
            },
        ) as span:
            try:
                result = await self.workflows[workflow_id].execute(
                    input_data, self.context
                )
                logger.info(f"Completed workflow '{workflow_id}'")
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute(ERROR_TYPE, type(exc).__name__)
                span.set_attribute(ERROR_MESSAGE, str(exc))
                raise


__all__ = ["AlphaApp"]
