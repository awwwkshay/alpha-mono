from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alpha_core.contracts.evals.scorer_contract import ScorerResult
from alpha_app.evals.scorers.answer_relevancy import AnswerRelevancyScorer
from alpha_app.evals.scorers.bias import BiasScorer
from alpha_app.evals.scorers.completeness import CompletenessScorer
from alpha_app.evals.scorers.faithfulness import FaithfulnessScorer
from alpha_app.evals.scorers.hallucination import HallucinationScorer
from alpha_app.evals.scorers.keyword_coverage import KeywordCoverageScorer
from alpha_app.evals.scorers.toxicity import ToxicityScorer


# ---------------------------------------------------------------------------
# KeywordCoverageScorer (rule-based — no mocking needed)
# ---------------------------------------------------------------------------


async def test_keyword_coverage_no_keywords_returns_perfect():
    scorer = KeywordCoverageScorer(keywords=[])
    result = await scorer.score("", "any output")
    assert result.score == 1.0


async def test_keyword_coverage_all_found_case_insensitive():
    scorer = KeywordCoverageScorer(keywords=["python", "async"])
    result = await scorer.score("", "Python is great for Async programming")
    assert result.score == 1.0


async def test_keyword_coverage_partial_coverage():
    scorer = KeywordCoverageScorer(keywords=["alpha", "beta", "gamma"])
    result = await scorer.score("", "alpha and gamma are present")
    assert result.score == pytest.approx(2 / 3)
    assert "beta" in (result.reason or "")


async def test_keyword_coverage_none_found():
    scorer = KeywordCoverageScorer(keywords=["missing", "absent"])
    result = await scorer.score("", "nothing relevant here")
    assert result.score == 0.0


async def test_keyword_coverage_case_sensitive_match():
    scorer = KeywordCoverageScorer(keywords=["Python"], case_sensitive=True)
    result = await scorer.score("", "Python is here")
    assert result.score == 1.0


async def test_keyword_coverage_case_sensitive_no_match():
    scorer = KeywordCoverageScorer(keywords=["Python"], case_sensitive=True)
    result = await scorer.score("", "python is here")
    assert result.score == 0.0


async def test_keyword_coverage_reason_lists_missing():
    scorer = KeywordCoverageScorer(keywords=["alpha", "beta"])
    result = await scorer.score("", "alpha present")
    assert result.reason is not None
    assert "beta" in result.reason


async def test_keyword_coverage_all_present_no_missing_in_reason():
    scorer = KeywordCoverageScorer(keywords=["alpha"])
    result = await scorer.score("", "alpha is here")
    assert result.reason is not None
    assert "missing" not in result.reason.lower()


# ---------------------------------------------------------------------------
# LLM-backed scorers — mocked acompletion
# ---------------------------------------------------------------------------


def _make_llm_response(score: int = 8, reason: str = "looks good") -> MagicMock:
    content = json.dumps({"score": score, "reason": reason})
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


async def test_answer_relevancy_scorer_normalises_score():
    scorer = AnswerRelevancyScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=8))
    ):
        result = await scorer.score("question", "answer")
    assert result.score == pytest.approx(0.8)
    assert isinstance(result, ScorerResult)


async def test_answer_relevancy_scorer_passes_reason():
    scorer = AnswerRelevancyScorer(model="test/m")
    with patch(
        "litellm.acompletion",
        AsyncMock(return_value=_make_llm_response(score=5, reason="meh")),
    ):
        result = await scorer.score("q", "a")
    assert result.reason == "meh"


async def test_completeness_scorer():
    scorer = CompletenessScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=10))
    ):
        result = await scorer.score("q", "a")
    assert result.score == pytest.approx(1.0)


async def test_faithfulness_scorer():
    scorer = FaithfulnessScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=6))
    ):
        result = await scorer.score("context", "response")
    assert result.score == pytest.approx(0.6)


async def test_hallucination_scorer_has_lower_is_better_metadata():
    scorer = HallucinationScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=3))
    ):
        result = await scorer.score("input", "output")
    assert result.score == pytest.approx(0.3)
    assert result.metadata.get("lower_is_better") is True


async def test_toxicity_scorer_has_lower_is_better_metadata():
    scorer = ToxicityScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=0))
    ):
        result = await scorer.score("", "safe text")
    assert result.score == pytest.approx(0.0)
    assert result.metadata.get("lower_is_better") is True


async def test_bias_scorer_has_lower_is_better_metadata():
    scorer = BiasScorer(model="test/m")
    with patch(
        "litellm.acompletion", AsyncMock(return_value=_make_llm_response(score=2))
    ):
        result = await scorer.score("", "biased text")
    assert result.score == pytest.approx(0.2)
    assert result.metadata.get("lower_is_better") is True
