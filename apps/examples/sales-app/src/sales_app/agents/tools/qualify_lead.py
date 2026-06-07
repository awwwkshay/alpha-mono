from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, Field

from clay_core import AgentTool, AppContext


class QualifyLeadInput(BaseModel):
    company_name: str
    industry: str | None = None
    company_size: int | None = Field(default=None, ge=1)
    annual_revenue_usd: float | None = Field(default=None, ge=0)
    pain_points: list[str] = Field(default_factory=list)
    budget_confirmed: bool = False
    authority_level: str = "unknown"
    timeline_months: int | None = Field(default=None, ge=0)
    existing_solution: str | None = None
    notes: str | None = None


class QualifyLeadOutput(BaseModel):
    score: int
    grade: str
    priority: str
    fit_summary: str
    recommended_next_step: str
    discovery_questions: list[str]
    risks: list[str]


Input: TypeAlias = QualifyLeadInput
Output: TypeAlias = QualifyLeadOutput


def _authority_score(authority_level: str) -> int:
    normalized = authority_level.strip().lower()
    if normalized in {"decision-maker", "decision maker", "economic buyer", "owner"}:
        return 20
    if normalized in {"influencer", "champion", "technical buyer"}:
        return 12
    if normalized in {"user", "evaluator"}:
        return 6
    return 0


def _timeline_score(timeline_months: int | None) -> int:
    if timeline_months is None:
        return 0
    if timeline_months <= 1:
        return 20
    if timeline_months <= 3:
        return 16
    if timeline_months <= 6:
        return 10
    return 4


def _grade(score: int) -> tuple[str, str]:
    if score >= 80:
        return "A", "high"
    if score >= 60:
        return "B", "medium"
    if score >= 40:
        return "C", "low"
    return "D", "nurture"


def _budget_signals(inp: Input) -> tuple[int, list[str], list[str]]:
    if inp.budget_confirmed:
        return 20, [], []
    return (
        0,
        ["Budget has not been confirmed."],
        ["What budget range has been allocated for solving this problem?"],
    )


def _authority_signals(inp: Input) -> tuple[int, list[str], list[str]]:
    score = _authority_score(inp.authority_level)
    if score >= 12:
        return score, [], []
    return (
        score,
        ["Decision authority is unclear or weak."],
        ["Who signs off on this purchase and who else influences the decision?"],
    )


def _timeline_signals(inp: Input) -> tuple[int, list[str], list[str]]:
    score = _timeline_score(inp.timeline_months)
    if inp.timeline_months is None:
        return (
            score,
            ["Purchase timeline is unknown."],
            ["When do you need a solution in place?"],
        )
    if inp.timeline_months > 6:
        return score, ["Timeline is longer than six months."], []
    return score, [], []


def _pain_signals(inp: Input) -> tuple[int, list[str], list[str]]:
    pain_count = len([point for point in inp.pain_points if point.strip()])
    if pain_count == 0:
        return (
            0,
            ["No clear pain points were captured."],
            ["What business problem is most urgent for your team right now?"],
        )
    return min(pain_count * 8, 24), [], []


def _company_fit_score(inp: Input) -> tuple[int, list[str], list[str]]:
    score = 0
    risks: list[str] = []
    questions: list[str] = []

    if inp.company_size is None:
        questions.append("How many employees are in the team or company?")
    elif inp.company_size >= 500:
        score += 16
    elif inp.company_size >= 100:
        score += 10
    elif inp.company_size >= 25:
        score += 6
    else:
        risks.append("Company size may be below the ideal customer profile.")

    if inp.annual_revenue_usd is not None:
        if inp.annual_revenue_usd >= 50_000_000:
            score += 12
        elif inp.annual_revenue_usd >= 10_000_000:
            score += 8
        elif inp.annual_revenue_usd >= 1_000_000:
            score += 4

    return score, risks, questions


def _current_solution_questions(inp: Input) -> tuple[int, list[str]]:
    if inp.existing_solution:
        return 4, [f"What is missing from {inp.existing_solution}?"]
    return 0, ["What are you using today to handle this workflow?"]


def _recommended_next_step(priority: str) -> str:
    if priority == "high":
        return "Schedule a discovery call with the economic buyer and prepare a tailored demo."
    if priority == "medium":
        return "Run a focused qualification call and confirm budget, authority, and timeline."
    if priority == "low":
        return "Nurture with relevant proof points while collecting missing qualification data."
    return "Keep in a nurture sequence until pain, budget, and timing become clearer."


async def _execute(inp: Input, ctx: AppContext) -> Output:
    _ = ctx
    score = 0
    risks: list[str] = []
    questions: list[str] = []

    for signal_score, signal_risks, signal_questions in (
        _budget_signals(inp),
        _authority_signals(inp),
        _timeline_signals(inp),
        _pain_signals(inp),
        _company_fit_score(inp),
    ):
        score += signal_score
        risks.extend(signal_risks)
        questions.extend(signal_questions)

    solution_score, solution_questions = _current_solution_questions(inp)
    score += solution_score
    questions.extend(solution_questions)

    score = min(score, 100)
    grade, priority = _grade(score)

    pain_summary = (
        ", ".join(inp.pain_points[:3]) if inp.pain_points else "no stated pain"
    )
    fit_summary = (
        f"{inp.company_name} is a grade {grade} lead with {pain_summary}. "
        f"Priority is {priority} based on budget, authority, timeline, and fit signals."
    )

    return Output(
        score=score,
        grade=grade,
        priority=priority,
        fit_summary=fit_summary,
        recommended_next_step=_recommended_next_step(priority),
        discovery_questions=questions[:5],
        risks=risks,
    )


qualify_lead_tool: AgentTool[QualifyLeadInput, QualifyLeadOutput] = AgentTool(
    name="Qualify Lead",
    description="Scores and summarizes a sales prospect using qualification signals.",
    input_schema=QualifyLeadInput,
    output_schema=QualifyLeadOutput,
    execute=_execute,
)

__all__ = ["qualify_lead_tool"]
