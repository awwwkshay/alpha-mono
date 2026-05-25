from dotenv import load_dotenv

from core.agent import Agent
from core.schemas.app_config import AppConfig
from core.schemas.app_context import AppContext
from core.types.app_id import AppId
from core.workflow import Workflow


class AlphaApp:
    config: AppConfig
    context: AppContext
    agents: dict[AppId, Agent]
    workflows: dict[AppId, Workflow]

    def __init__(self, *, config: AppConfig):
        load_dotenv(dotenv_path=config.env_file)
        self.config = config
        self.agents = {
            app_id: Agent(config=agent_config)
            for app_id, agent_config in config.agents.items()
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

    async def execute_workflow(self, workflow_id: AppId, input_data: dict) -> dict:
        return await self.workflows[workflow_id].execute(input_data, self.context)


__all__ = ["AlphaApp"]
