from __future__ import annotations

from clay_app import (
    AnswerRelevancyScorer,
    CompletenessScorer,
    ToxicityScorer,
)
from clay_core import (
    AgentConfig,
    SamplingConfig,
    ScorerConfig,
)

EVAL_MODEL = "gemini/gemini-2.0-flash"

AGENTS: dict[str, AgentConfig] = {
    "parser": AgentConfig(
        name="Code Parser",
        system_prompt=(
            "You analyze code structure concisely. Follow output formats exactly."
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
        scorers={
            "completeness": ScorerConfig(
                scorer=CompletenessScorer(model=EVAL_MODEL),
                sampling=SamplingConfig(rate=0.5),
            ),
        },
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
        scorers={
            "relevancy": ScorerConfig(
                scorer=AnswerRelevancyScorer(model=EVAL_MODEL),
            ),
            "completeness": ScorerConfig(
                scorer=CompletenessScorer(model=EVAL_MODEL),
            ),
            "toxicity": ScorerConfig(
                scorer=ToxicityScorer(model=EVAL_MODEL),
            ),
        },
    ),
}

__all__ = ["AGENTS", "EVAL_MODEL"]
