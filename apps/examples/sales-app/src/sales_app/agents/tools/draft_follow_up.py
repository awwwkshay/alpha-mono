from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from clay_core import AgentTool, AppContext


Tone = Literal["concise", "consultative", "executive"]


class DraftFollowUpInput(BaseModel):
    prospect_name: str
    company_name: str
    pain_points: list[str] = Field(default_factory=list)
    promised_next_step: str
    meeting_summary: str | None = None
    tone: Tone = "consultative"


class DraftFollowUpOutput(BaseModel):
    subject: str
    email_body: str
    call_to_action: str


Input: TypeAlias = DraftFollowUpInput
Output: TypeAlias = DraftFollowUpOutput


def _opening(tone: Tone, prospect_name: str) -> str:
    if tone == "executive":
        return f"{prospect_name}, thanks for the time today."
    if tone == "concise":
        return f"Hi {prospect_name}, thanks for speaking today."
    return f"Hi {prospect_name}, I appreciated the conversation today."


async def _execute(inp: Input, ctx: AppContext) -> Output:
    _ = ctx
    pains = (
        ", ".join(inp.pain_points) if inp.pain_points else "the priorities we discussed"
    )
    summary = f"\n\nMy notes: {inp.meeting_summary}" if inp.meeting_summary else ""
    call_to_action = inp.promised_next_step
    body = (
        f"{_opening(inp.tone, inp.prospect_name)}\n\n"
        f"It sounds like {inp.company_name} is focused on {pains}."
        f"{summary}\n\n"
        f"Next step: {call_to_action}\n\n"
        "Best,\n"
    )
    return Output(
        subject=f"Next steps for {inp.company_name}",
        email_body=body,
        call_to_action=call_to_action,
    )


draft_follow_up_tool: AgentTool[DraftFollowUpInput, DraftFollowUpOutput] = AgentTool(
    name="Draft Follow Up",
    description="Drafts a sales follow-up email from meeting notes, pain points, and next steps.",
    input_schema=DraftFollowUpInput,
    output_schema=DraftFollowUpOutput,
    execute=_execute,
)

__all__ = ["draft_follow_up_tool"]
