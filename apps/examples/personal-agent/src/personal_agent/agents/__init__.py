from __future__ import annotations

from personal_agent.agents.jarvis import AGENT as JARVIS_AGENT
from personal_agent.agents.jarvis import personal_agent, personal_agent_config

AGENTS = {
    "jarvis": JARVIS_AGENT,
}

__all__ = ["AGENTS", "JARVIS_AGENT", "personal_agent_config", "personal_agent"]
