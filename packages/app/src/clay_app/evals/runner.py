from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from clay_core import Scorer, ScorerConfig, ScorerResult

if TYPE_CHECKING:
    from clay_app.agent.agent import Agent
    from clay_core import AppContext


class EvalCase(BaseModel):
    input: str
    expected_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    case: EvalCase
    output: str
    scores: dict[str, ScorerResult]


async def run_scorers(
    scorers: dict[str, ScorerConfig],
    input: str,
    output: str,
) -> dict[str, ScorerResult]:
    active = {name: cfg for name, cfg in scorers.items() if cfg.should_run()}
    if not active:
        return {}

    results = await asyncio.gather(
        *[cfg.scorer.score(input, output) for cfg in active.values()],
        return_exceptions=True,
    )

    return {
        name: result
        for name, result in zip(active.keys(), results)
        if isinstance(result, ScorerResult)
    }


async def run_evals(
    *,
    target: Agent,
    data: list[EvalCase],
    scorers: list[Scorer],
    context: AppContext,
) -> list[EvalResult]:
    named_scorers = {type(s).__name__: ScorerConfig(scorer=s) for s in scorers}

    async def _eval_one(case: EvalCase) -> EvalResult:
        output = await target.generate_async(case.input, context)
        scores = await run_scorers(named_scorers, case.input, output)
        return EvalResult(case=case, output=output, scores=scores)

    return list(await asyncio.gather(*[_eval_one(case) for case in data]))


__all__ = ["EvalCase", "EvalResult", "run_evals", "run_scorers"]
