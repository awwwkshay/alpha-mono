from __future__ import annotations

from pathlib import Path

from alpha_app import Agent, AgentConfig, SlackChat

from personal_agent.agents.tools.datetime_tool import get_datetime_tool
from personal_agent.agents.tools.summarise_url_tool import summarise_url_tool
from personal_agent.agents.tools.web_search_tool import web_search_tool
from personal_agent.workflows.daily_brief import daily_brief_workflow
from personal_agent.workflows.research_summarise import research_summarise_workflow

_PROMPT_PATH = Path(__file__).parents[2] / "prompts" / "jarvis.md"

personal_agent_config = AgentConfig(
    name="Jarvis",
    system_prompt_md_path=_PROMPT_PATH,
    model="gemini/gemini-flash-latest",
    tools={
        "get_current_datetime": get_datetime_tool,
        "web_search": web_search_tool,
        "summarise_url": summarise_url_tool,
    },
    workflows={
        "daily_brief": daily_brief_workflow,
        "research_summarise": research_summarise_workflow,
    },
    chat=[SlackChat()],
)

personal_agent = Agent(config=personal_agent_config)

__all__ = ["personal_agent_config", "personal_agent"]
