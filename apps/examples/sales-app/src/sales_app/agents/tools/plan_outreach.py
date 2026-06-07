from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from clay_core import AgentTool, AppContext


Persona = Literal[
    "founder",
    "sales leader",
    "marketing leader",
    "operations leader",
    "technical buyer",
]


class PlanOutreachInput(BaseModel):
    company_name: str
    persona: Persona
    business_goal: str
    value_proposition: str
    channels: list[str] = Field(default_factory=lambda: ["email", "linkedin", "call"])
    sequence_days: int = Field(default=10, ge=3, le=30)


class OutreachStep(BaseModel):
    day: int
    channel: str
    objective: str
    message_angle: str


class PlanOutreachOutput(BaseModel):
    sequence_name: str
    steps: list[OutreachStep]
    success_metric: str


Input: TypeAlias = PlanOutreachInput
Output: TypeAlias = PlanOutreachOutput


def _channel(channels: list[str], index: int) -> str:
    if not channels:
        return "email"
    return channels[index % len(channels)]


async def _execute(inp: Input, ctx: AppContext) -> Output:
    _ = ctx
    spacing = max(inp.sequence_days // 4, 1)
    steps = [
        OutreachStep(
            day=1,
            channel=_channel(inp.channels, 0),
            objective="Open the conversation",
            message_angle=f"Connect {inp.value_proposition} to {inp.business_goal}.",
        ),
        OutreachStep(
            day=1 + spacing,
            channel=_channel(inp.channels, 1),
            objective="Share relevant proof",
            message_angle=f"Show how similar {inp.persona}s improved {inp.business_goal}.",
        ),
        OutreachStep(
            day=1 + spacing * 2,
            channel=_channel(inp.channels, 2),
            objective="Create urgency",
            message_angle=f"Highlight the cost of delaying work on {inp.business_goal}.",
        ),
        OutreachStep(
            day=inp.sequence_days,
            channel=_channel(inp.channels, 3),
            objective="Ask for a clear yes or no",
            message_angle="Offer a short discovery call or permission to close the loop.",
        ),
    ]
    return Output(
        sequence_name=f"{inp.company_name} {inp.persona} outreach",
        steps=steps,
        success_metric="Positive reply or booked discovery meeting",
    )


plan_outreach_tool: AgentTool[PlanOutreachInput, PlanOutreachOutput] = AgentTool(
    name="Plan Outreach",
    description="Builds a multi-touch outbound sequence for a target account and buyer persona.",
    input_schema=PlanOutreachInput,
    output_schema=PlanOutreachOutput,
    execute=_execute,
)

__all__ = ["plan_outreach_tool"]
