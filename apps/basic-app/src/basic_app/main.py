import asyncio
from pathlib import Path
from textwrap import dedent

from core.app import AlphaApp
from core.schemas.agent_config import AgentConfig
from core.schemas.app_config import AppConfig
from core.schemas.app_context import AppContext
from core.schemas.workflow_config import (
    ConditionalWorkflowStepConfig,
    ParallelWorkflowStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)
from pydantic import BaseModel

ENV_FILE = Path(__file__).parents[2] / ".env"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CodeReview(BaseModel):
    code: str
    language: str


class CodeSummary(BaseModel):
    code: str
    language: str
    purpose: str
    patterns: list[str]


# --- parallel branch outputs (non-overlapping fields) ---


class SecurityOut(BaseModel):
    security_issues: str
    severity: str  # "high" | "medium" | "low"


class PerformanceOut(BaseModel):
    performance_issues: str


class StyleOut(BaseModel):
    style_issues: str


# --- merged parallel output ---


class ReviewDraft(BaseModel):
    security_issues: str
    severity: str
    performance_issues: str
    style_issues: str


# --- final report ---


class ReviewReport(BaseModel):
    verdict: str
    priority_issues: list[str]
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Step 1 — Parse: understand the code before reviewing it
# ---------------------------------------------------------------------------


async def parse_code(input: CodeReview, context: AppContext) -> CodeSummary:
    agent = context.agents["parser"]
    response = await agent.generate_async(
        dedent(f"""
            Analyze this {input.language} code and respond in this exact format:
            PURPOSE: <one sentence>
            PATTERNS: <comma-separated list of design patterns or techniques used>

            Code:
            {input.code}
        """),
        context,
    )
    purpose, patterns_raw = "", []
    for line in response.splitlines():
        if line.startswith("PURPOSE:"):
            purpose = line.removeprefix("PURPOSE:").strip()
        elif line.startswith("PATTERNS:"):
            patterns_raw = [
                p.strip()
                for p in line.removeprefix("PATTERNS:").split(",")
                if p.strip()
            ]
    return CodeSummary(
        code=input.code,
        language=input.language,
        purpose=purpose,
        patterns=patterns_raw,
    )


# ---------------------------------------------------------------------------
# Step 2 — Parallel: security + performance + style run concurrently
# ---------------------------------------------------------------------------


async def security_review(input: CodeSummary, context: AppContext) -> SecurityOut:
    agent = context.agents["security_reviewer"]
    response = await agent.generate_async(
        dedent(f"""
            Review this {input.language} code for security vulnerabilities.
            Respond in this exact format:
            ISSUES: <describe issues found, or "none">
            SEVERITY: <high|medium|low>

            Code purpose: {input.purpose}
            Code:
            {input.code}
        """),
        context,
    )
    issues, severity = "none", "low"
    for line in response.splitlines():
        if line.startswith("ISSUES:"):
            issues = line.removeprefix("ISSUES:").strip()
        elif line.startswith("SEVERITY:"):
            raw = line.removeprefix("SEVERITY:").strip().lower()
            severity = raw if raw in ("high", "medium", "low") else "low"
    return SecurityOut(security_issues=issues, severity=severity)


async def performance_review(input: CodeSummary, context: AppContext) -> PerformanceOut:
    agent = context.agents["performance_reviewer"]
    response = await agent.generate_async(
        dedent(f"""
            Review this {input.language} code for performance issues
            (complexity, memory, unnecessary work).
            Be specific and concise. If no issues, say "none".

            Code purpose: {input.purpose}
            Code:
            {input.code}
        """),
        context,
    )
    return PerformanceOut(performance_issues=response.strip())


async def style_review(input: CodeSummary, context: AppContext) -> StyleOut:
    agent = context.agents["style_reviewer"]
    response = await agent.generate_async(
        dedent(f"""
            Review this {input.language} code for style issues:
            naming, readability, structure, best practices.
            Be specific and concise. If no issues, say "none".

            Code purpose: {input.purpose}
            Patterns used: {", ".join(input.patterns)}
            Code:
            {input.code}
        """),
        context,
    )
    return StyleOut(style_issues=response.strip())


# ---------------------------------------------------------------------------
# Step 3 — Conditional: severity from security review routes to different reports
# ---------------------------------------------------------------------------


def route_by_severity(input: ReviewDraft, context: AppContext) -> str:
    return "urgent" if input.severity == "high" else "standard"


async def urgent_report(input: ReviewDraft, context: AppContext) -> ReviewReport:
    """Security-critical path: leads with the vulnerability,
    demands immediate action."""
    agent = context.agents["report_writer"]
    response = await agent.generate_async(
        dedent(f"""
            Write an URGENT security-focused code review report.
            Lead with the security vulnerability and mark it as blocking.
            Respond in this exact format:
            VERDICT: <one sentence verdict starting with "BLOCKING:">
            PRIORITY_ISSUES: <issue 1> | <issue 2> | <issue 3>
            RECOMMENDATIONS: <action 1> | <action 2> | <action 3>

            Security issues (HIGH): {input.security_issues}
            Performance issues: {input.performance_issues}
            Style issues: {input.style_issues}
        """),
        context,
    )
    return _parse_report(response)


async def standard_report(input: ReviewDraft, context: AppContext) -> ReviewReport:
    """Standard path: balanced review across all dimensions."""
    agent = context.agents["report_writer"]
    response = await agent.generate_async(
        dedent(f"""
            Write a balanced code review report covering security,
            performance, and style.
            Respond in this exact format:
            VERDICT: <one sentence overall verdict>
            PRIORITY_ISSUES: <issue 1> | <issue 2> | <issue 3>
            RECOMMENDATIONS: <action 1> | <action 2> | <action 3>

            Security issues ({input.severity}): {input.security_issues}
            Performance issues: {input.performance_issues}
            Style issues: {input.style_issues}
        """),
        context,
    )
    return _parse_report(response)


def _parse_report(response: str) -> ReviewReport:
    verdict, priority_issues, recommendations = "", [], []
    for line in response.splitlines():
        if line.startswith("VERDICT:"):
            verdict = line.removeprefix("VERDICT:").strip()
        elif line.startswith("PRIORITY_ISSUES:"):
            priority_issues = [
                i.strip()
                for i in line.removeprefix("PRIORITY_ISSUES:").split("|")
                if i.strip()
            ]
        elif line.startswith("RECOMMENDATIONS:"):
            recommendations = [
                r.strip()
                for r in line.removeprefix("RECOMMENDATIONS:").split("|")
                if r.strip()
            ]
    return ReviewReport(
        verdict=verdict,
        priority_issues=priority_issues,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


async def main() -> None:
    config = AppConfig(
        name="code-reviewer",
        env_file=ENV_FILE,
        agents={
            "parser": AgentConfig(
                name="Code Parser",
                system_prompt=(
                    "You analyze code structure concisely. "
                    "Follow output formats exactly."
                ),
                model="gemini/gemini-2.0-flash",
            ),
            "security_reviewer": AgentConfig(
                name="Security Reviewer",
                system_prompt=(
                    "You are a senior application security engineer. "
                    "Identify vulnerabilities: injection, auth issues, "
                    "data exposure, insecure dependencies. "
                    "Follow output formats exactly."
                ),
                model="gemini/gemini-2.0-flash",
            ),
            "performance_reviewer": AgentConfig(
                name="Performance Reviewer",
                system_prompt=(
                    "You are a performance engineering expert. "
                    "Identify algorithmic complexity issues, memory "
                    "inefficiencies, and unnecessary work. "
                    "Be specific and concise."
                ),
                model="gemini/gemini-2.0-flash",
            ),
            "style_reviewer": AgentConfig(
                name="Style Reviewer",
                system_prompt=(
                    "You are a senior engineer focused on code quality. "
                    "Review naming, readability, structure, "
                    "and language best practices. "
                    "Be specific and concise."
                ),
                model="gemini/gemini-2.0-flash",
            ),
            "report_writer": AgentConfig(
                name="Report Writer",
                system_prompt=(
                    "You synthesize technical reviews into clear, actionable reports. "
                    "Follow output formats exactly. Be direct and specific."
                ),
                model="gemini/gemini-2.0-flash",
            ),
        },
        workflows={
            "review": WorkflowConfig.create(
                name="Code Review",
                input_schema=CodeReview,
                output_schema=ReviewReport,
                steps={
                    "parse": WorkflowStepConfig.create(
                        name="Parse Code",
                        input_schema=CodeReview,
                        output_schema=CodeSummary,
                        execute=parse_code,
                    ),
                    "analyze": ParallelWorkflowStepConfig.create(
                        name="Parallel Review",
                        input_schema=CodeSummary,
                        output_schema=ReviewDraft,
                        branches={
                            "security": WorkflowStepConfig.create(
                                name="Security",
                                input_schema=CodeSummary,
                                output_schema=SecurityOut,
                                execute=security_review,
                            ),
                            "performance": WorkflowStepConfig.create(
                                name="Performance",
                                input_schema=CodeSummary,
                                output_schema=PerformanceOut,
                                execute=performance_review,
                            ),
                            "style": WorkflowStepConfig.create(
                                name="Style",
                                input_schema=CodeSummary,
                                output_schema=StyleOut,
                                execute=style_review,
                            ),
                        },
                    ),
                    "report": ConditionalWorkflowStepConfig.create(
                        name="Write Report",
                        input_schema=ReviewDraft,
                        output_schema=ReviewReport,
                        condition=route_by_severity,
                        branches={
                            "urgent": WorkflowStepConfig.create(
                                name="Urgent Report",
                                input_schema=ReviewDraft,
                                output_schema=ReviewReport,
                                execute=urgent_report,
                            ),
                            "standard": WorkflowStepConfig.create(
                                name="Standard Report",
                                input_schema=ReviewDraft,
                                output_schema=ReviewReport,
                                execute=standard_report,
                            ),
                        },
                    ),
                },
            )
        },
    )

    app = AlphaApp(config=config)

    result = await app.execute_workflow(
        "review",
        {
            "language": "Python",
            "code": dedent("""
                from collections import Counter
                from pathlib import Path

                def count_chars(filename: str) -> list[tuple[str, int]]:
                    data = Path(filename).read_text()
                    return Counter(data).most_common()
            """).strip(),
        },
    )

    print(f"\nVerdict: {result['verdict']}")
    print("\nPriority Issues:")
    for issue in result["priority_issues"]:
        print(f"  • {issue}")
    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  • {rec}")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
