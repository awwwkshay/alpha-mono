from __future__ import annotations

from textwrap import dedent

from clay_core import AppContext

from basic_app.schemas import (
    CodeReview,
    CodeSummary,
    PerformanceOut,
    ReviewDraft,
    ReviewReport,
    SecurityOut,
    StyleOut,
)


async def parse_code(input: CodeReview, context: AppContext) -> CodeSummary:
    agent = context.agents["parser"]
    return await agent.generate_structured_async(
        dedent(f"""
            Analyze this {input.language} code and identify its purpose and the
            design patterns or techniques it uses.

            Code:
            {input.code}
        """),
        context,
        CodeSummary,
    )


async def security_review(input: CodeSummary, context: AppContext) -> SecurityOut:
    agent = context.agents["security_reviewer"]
    return await agent.generate_structured_async(
        dedent(f"""
            Review this {input.language} code for security vulnerabilities.

            Code purpose: {input.purpose}
            Code:
            {input.code}
        """),
        context,
        SecurityOut,
    )


async def performance_review(input: CodeSummary, context: AppContext) -> PerformanceOut:
    agent = context.agents["performance_reviewer"]
    return await agent.generate_structured_async(
        dedent(f"""
            Review this {input.language} code for performance issues
            (complexity, memory, unnecessary work). Be specific and concise.

            Code purpose: {input.purpose}
            Code:
            {input.code}
        """),
        context,
        PerformanceOut,
    )


async def style_review(input: CodeSummary, context: AppContext) -> StyleOut:
    agent = context.agents["style_reviewer"]
    return await agent.generate_structured_async(
        dedent(f"""
            Review this {input.language} code for style issues:
            naming, readability, structure, best practices.
            Be specific and concise.

            Code purpose: {input.purpose}
            Patterns used: {", ".join(input.patterns)}
            Code:
            {input.code}
        """),
        context,
        StyleOut,
    )


def route_by_severity(input: ReviewDraft, _context: AppContext) -> str:
    return "urgent" if input.severity == "high" else "standard"


async def urgent_report(input: ReviewDraft, context: AppContext) -> ReviewReport:
    agent = context.agents["report_writer"]
    return await agent.generate_structured_async(
        dedent(f"""
            Write an URGENT security-focused code review report.
            Lead with the security vulnerability and mark it as blocking.

            Security issues (HIGH): {input.security_issues}
            Performance issues: {input.performance_issues}
            Style issues: {input.style_issues}
        """),
        context,
        ReviewReport,
    )


async def standard_report(input: ReviewDraft, context: AppContext) -> ReviewReport:
    agent = context.agents["report_writer"]
    return await agent.generate_structured_async(
        dedent(f"""
            Write a balanced code review report covering security,
            performance, and style.

            Security issues ({input.severity}): {input.security_issues}
            Performance issues: {input.performance_issues}
            Style issues: {input.style_issues}
        """),
        context,
        ReviewReport,
    )


__all__ = [
    "parse_code",
    "performance_review",
    "route_by_severity",
    "security_review",
    "standard_report",
    "style_review",
    "urgent_report",
]
