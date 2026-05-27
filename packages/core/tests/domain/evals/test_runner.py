from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from alpha_core.domain.evals.runner import EvalCase, EvalResult, run_evals, run_scorers
from alpha_core.domain.evals.scorer import (
    Scorer,
    SamplingConfig,
    ScorerConfig,
    ScorerResult,
)
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext


class _FixedScorer(Scorer):
    def __init__(self, score: float = 0.8, *, raises: bool = False) -> None:
        self._score = score
        self._raises = raises

    async def score(self, input: str, output: str) -> ScorerResult:
        if self._raises:
            raise RuntimeError("scorer failed")
        return ScorerResult(score=self._score)


def _make_scorer_cfg(score: float = 0.8, *, raises: bool = False) -> ScorerConfig:
    return ScorerConfig(scorer=_FixedScorer(score, raises=raises))


def _make_context() -> AppContext:
    return AppContext(config=AppConfig(name="test"))


# ---------------------------------------------------------------------------
# run_scorers
# ---------------------------------------------------------------------------


async def test_run_scorers_all_active_run():
    scorers = {
        "s1": _make_scorer_cfg(0.9),
        "s2": _make_scorer_cfg(0.5),
    }
    results = await run_scorers(scorers, "input", "output")
    assert set(results.keys()) == {"s1", "s2"}
    assert results["s1"].score == 0.9
    assert results["s2"].score == 0.5


async def test_run_scorers_drops_exceptions():
    scorers = {
        "good": _make_scorer_cfg(0.7),
        "bad": _make_scorer_cfg(raises=True),
    }
    results = await run_scorers(scorers, "input", "output")
    assert "good" in results
    assert "bad" not in results


async def test_run_scorers_empty_dict_returns_empty():
    results = await run_scorers({}, "input", "output")
    assert results == {}


async def test_run_scorers_respects_sampling_rate_zero():
    scorer = _make_scorer_cfg(0.5)
    scorer.sampling = SamplingConfig(rate=0.0)
    results = await run_scorers({"s": scorer}, "input", "output")
    assert results == {}


async def test_run_scorers_all_raise_returns_empty():
    scorers = {
        "a": _make_scorer_cfg(raises=True),
        "b": _make_scorer_cfg(raises=True),
    }
    results = await run_scorers(scorers, "in", "out")
    assert results == {}


# ---------------------------------------------------------------------------
# run_evals
# ---------------------------------------------------------------------------


def _make_response_agent(response: str) -> MagicMock:
    agent = MagicMock()
    agent.generate_async = AsyncMock(return_value=response)
    return agent


async def test_run_evals_returns_one_result_per_case():
    cases = [EvalCase(input="q1"), EvalCase(input="q2")]
    agent = _make_response_agent("answer")

    results = await run_evals(
        target=agent,
        data=cases,
        scorers=[_FixedScorer(1.0)],
        context=_make_context(),
    )

    assert len(results) == 2
    assert all(isinstance(r, EvalResult) for r in results)


async def test_run_evals_stores_output_and_case():
    case = EvalCase(input="hello", expected_output="world")
    agent = _make_response_agent("world")

    results = await run_evals(
        target=agent, data=[case], scorers=[_FixedScorer(1.0)], context=_make_context()
    )

    assert results[0].output == "world"
    assert results[0].case is case


async def test_run_evals_uses_class_name_as_scorer_key():
    case = EvalCase(input="q")
    agent = _make_response_agent("a")

    class MyScorer(Scorer):
        async def score(self, input: str, output: str) -> ScorerResult:
            return ScorerResult(score=0.6)

    results = await run_evals(
        target=agent, data=[case], scorers=[MyScorer()], context=_make_context()
    )
    assert "MyScorer" in results[0].scores


async def test_run_evals_no_scorers_returns_empty_scores():
    case = EvalCase(input="q")
    agent = _make_response_agent("a")

    results = await run_evals(
        target=agent, data=[case], scorers=[], context=_make_context()
    )
    assert results[0].scores == {}
