from __future__ import annotations

import json

from alpha_core.domain.evals.scorer import Scorer, ScorerResult

_PROMPT = """\
Evaluate how complete and thorough the following response is for the given input.

Input: {input}
Response: {output}

Score from 0 to 10:
- 0: missing all key information
- 10: comprehensive, addresses all aspects of the input

Respond only with JSON: {{"score": <0-10>, "reason": "<one sentence>"}}"""


class CompletenessScorer(Scorer):
    def __init__(self, *, model: str) -> None:
        self._model = model

    async def score(self, input: str, output: str) -> ScorerResult:
        from litellm import acompletion

        response = await acompletion(
            model=self._model,
            messages=[
                {"role": "user", "content": _PROMPT.format(input=input, output=output)}
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return ScorerResult(
            score=float(data["score"]) / 10.0, reason=data.get("reason")
        )


__all__ = ["CompletenessScorer"]
