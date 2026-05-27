from __future__ import annotations

from textwrap import dedent

from alpha_core.schemas.app_context import AppContext

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


def route_by_severity(input: ReviewDraft, _context: AppContext) -> str:
    return "urgent" if input.severity == "high" else "standard"


async def urgent_report(input: ReviewDraft, context: AppContext) -> ReviewReport:
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


__all__ = [
    "parse_code",
    "performance_review",
    "route_by_severity",
    "security_review",
    "standard_report",
    "style_review",
    "urgent_report",
]
