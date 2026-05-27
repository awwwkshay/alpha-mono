from __future__ import annotations

from textwrap import dedent

from alpha_core.domain.agent.agent import Agent
from alpha_core.domain.evals.runner import EvalCase, EvalResult, run_evals
from alpha_core.contracts.evals.scorer_contract import Scorer
from alpha_core.domain.evals.scorers import AnswerRelevancyScorer, CompletenessScorer
from alpha_core.schemas.app_context import AppContext

from basic_app.agents import EVAL_MODEL

EVAL_CASES: list[EvalCase] = [
    EvalCase(
        input=dedent("""
            Analyze this Python code and respond in this exact format:
            PURPOSE: <one sentence>
            PATTERNS: <comma-separated list>

            Code:
            def add(a, b): return a + b
        """),
    ),
    EvalCase(
        input=dedent("""
            Analyze this Python code and respond in this exact format:
            PURPOSE: <one sentence>
            PATTERNS: <comma-separated list>

            Code:
            class Singleton:
                _instance = None
                def __new__(cls):
                    if not cls._instance:
                        cls._instance = super().__new__(cls)
                    return cls._instance
        """),
    ),
    EvalCase(
        input=dedent("""
            Analyze this Python code and respond in this exact format:
            PURPOSE: <one sentence>
            PATTERNS: <comma-separated list>

            Code:
            x=1
        """),
    ),
    EvalCase(
        input=dedent("""
            Analyze this Python code and respond in this exact format:
            PURPOSE: <one sentence>
            PATTERNS: <comma-separated list>

            Code:
        """),
    ),
]

EVAL_SCORERS: list[Scorer] = [
    AnswerRelevancyScorer(model=EVAL_MODEL),
    CompletenessScorer(model=EVAL_MODEL),
]


async def run_parser_evals(agent: Agent, context: AppContext) -> list[EvalResult]:
    return await run_evals(
        target=agent,
        data=EVAL_CASES,
        scorers=EVAL_SCORERS,
        context=context,
    )


def print_eval_results(results: list[EvalResult]) -> None:
    print("\n=== Eval Results ===")
    for i, result in enumerate(results, 1):
        print(f"\nCase {i}:")
        print(f"  Output: {result.output[:80].strip()}...")
        for name, score in result.scores.items():
            print(f"  [{name}] score={score.score:.2f}  reason={score.reason}")


__all__ = [
    "EVAL_CASES",
    "EVAL_SCORERS",
    "print_eval_results",
    "run_parser_evals",
]
