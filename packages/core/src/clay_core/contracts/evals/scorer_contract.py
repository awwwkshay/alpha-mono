from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScorerResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scorer(ABC):
    @abstractmethod
    async def score(self, input: str, output: str) -> ScorerResult: ...


class SamplingConfig(BaseModel):
    rate: float = Field(default=1.0, ge=0.0, le=1.0)


class ScorerConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scorer: Scorer
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)

    def should_run(self) -> bool:
        return random.random() < self.sampling.rate


__all__ = ["Scorer", "ScorerConfig", "ScorerResult", "SamplingConfig"]
