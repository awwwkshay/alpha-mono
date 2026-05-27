from __future__ import annotations

import pytest
from pydantic import ValidationError

from alpha_core.domain.evals.scorer import (
    Scorer,
    SamplingConfig,
    ScorerConfig,
    ScorerResult,
)


class _NoopScorer(Scorer):
    async def score(self, input: str, output: str) -> ScorerResult:
        return ScorerResult(score=1.0)


# ---------------------------------------------------------------------------
# ScorerResult
# ---------------------------------------------------------------------------


def test_scorer_result_valid():
    r = ScorerResult(score=0.75)
    assert r.score == 0.75
    assert r.reason is None
    assert r.metadata == {}


def test_scorer_result_with_reason_and_metadata():
    r = ScorerResult(score=0.5, reason="ok", metadata={"k": "v"})
    assert r.reason == "ok"
    assert r.metadata == {"k": "v"}


def test_scorer_result_score_zero():
    r = ScorerResult(score=0.0)
    assert r.score == 0.0


def test_scorer_result_score_one():
    r = ScorerResult(score=1.0)
    assert r.score == 1.0


def test_scorer_result_score_below_zero_raises():
    with pytest.raises(ValidationError):
        ScorerResult(score=-0.1)


def test_scorer_result_score_above_one_raises():
    with pytest.raises(ValidationError):
        ScorerResult(score=1.1)


# ---------------------------------------------------------------------------
# SamplingConfig
# ---------------------------------------------------------------------------


def test_sampling_config_default_rate():
    cfg = SamplingConfig()
    assert cfg.rate == 1.0


def test_sampling_config_custom_rate():
    cfg = SamplingConfig(rate=0.3)
    assert cfg.rate == 0.3


def test_sampling_config_rate_below_zero_raises():
    with pytest.raises(ValidationError):
        SamplingConfig(rate=-0.1)


def test_sampling_config_rate_above_one_raises():
    with pytest.raises(ValidationError):
        SamplingConfig(rate=1.1)


# ---------------------------------------------------------------------------
# ScorerConfig.should_run
# ---------------------------------------------------------------------------


def test_scorer_config_should_run_rate_one():
    cfg = ScorerConfig(scorer=_NoopScorer(), sampling=SamplingConfig(rate=1.0))
    assert cfg.should_run() is True


def test_scorer_config_should_run_rate_zero():
    cfg = ScorerConfig(scorer=_NoopScorer(), sampling=SamplingConfig(rate=0.0))
    assert cfg.should_run() is False


def test_scorer_config_should_run_default_rate_always():
    cfg = ScorerConfig(scorer=_NoopScorer())
    # Default rate=1.0 → always True
    assert cfg.should_run() is True


def test_scorer_config_should_run_sampling(monkeypatch):
    import random

    cfg = ScorerConfig(scorer=_NoopScorer(), sampling=SamplingConfig(rate=0.5))

    monkeypatch.setattr(random, "random", lambda: 0.3)
    assert cfg.should_run() is True  # 0.3 < 0.5

    monkeypatch.setattr(random, "random", lambda: 0.7)
    assert cfg.should_run() is False  # 0.7 >= 0.5
