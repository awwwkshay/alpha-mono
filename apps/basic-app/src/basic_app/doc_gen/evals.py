from __future__ import annotations

from pathlib import Path

from alpha_app import (
    Agent,
    AnswerRelevancyScorer,
    AppContext,
    CompletenessScorer,
    EvalCase,
    EvalResult,
    Scorer,
    run_evals,
)

_EVAL_MODEL = "gemini/gemini-2.0-flash"
_SOURCE_DIR = Path(__file__).parents[3]

DOC_GEN_EVAL_CASES: list[EvalCase] = [
    EvalCase(
        input=(
            "Write a concise summary for this Python module.\n\n"
            "File: basic_app/doc_gen/schemas.py\n"
            "Purpose: Defines Pydantic models for the documentation generator workflow\n"
            "Type: domain_model\n"
            "Public functions: none\n"
            "Public classes: DocGenInput, FileContent, PurposeOut, ApiSurfaceOut, "
            "ComplexityOut, AnalysisDraft, DocOutput\n"
        ),
    ),
    EvalCase(
        input=(
            "Write a concise summary for this Python module.\n\n"
            "File: basic_app/schemas.py\n"
            "Purpose: Defines Pydantic models for the code review workflow\n"
            "Type: domain_model\n"
            "Public functions: none\n"
            "Public classes: CodeReview, CodeSummary, SecurityOut, PerformanceOut, "
            "StyleOut, ReviewDraft, ReviewReport\n"
        ),
    ),
]

DOC_GEN_EVAL_SCORERS: list[Scorer] = [
    AnswerRelevancyScorer(model=_EVAL_MODEL),
    CompletenessScorer(model=_EVAL_MODEL),
]


async def run_doc_gen_evals(agent: Agent, context: AppContext) -> list[EvalResult]:
    return await run_evals(
        target=agent,
        data=DOC_GEN_EVAL_CASES,
        scorers=DOC_GEN_EVAL_SCORERS,
        context=context,
    )


def print_doc_gen_eval_results(results: list[EvalResult]) -> None:
    print("\n=== Doc Gen Eval Results ===")
    for i, result in enumerate(results, 1):
        print(f"\nCase {i}:")
        print(f"  Output: {result.output[:100].strip()}...")
        for name, score in result.scores.items():
            print(f"  [{name}] score={score.score:.2f}  reason={score.reason}")


__all__ = [
    "DOC_GEN_EVAL_CASES",
    "DOC_GEN_EVAL_SCORERS",
    "print_doc_gen_eval_results",
    "run_doc_gen_evals",
]
