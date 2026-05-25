from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    name: str = Field(..., description="The name of the agent")
    system_prompt: str = Field(..., description="The system prompt for the agent")
    model: str = Field(..., description="The model to use for the agent")
    description: str | None = Field(
        default=None, description="A brief description of the agent"
    )


__all__ = ["AgentConfig"]
