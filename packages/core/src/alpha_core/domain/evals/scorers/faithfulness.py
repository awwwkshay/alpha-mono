from __future__ import annotations

import json

from alpha_core.contracts.evals.scorer_contract import Scorer, ScorerResult

_PROMPT = """\
Evaluate how faithful the following response is — does it avoid introducing claims \
not supported by the input context?

Input/Context: {input}
Response: {output}

Score from 0 to 10:
- 0: contains many unsupported or fabricated claims
- 10: every statement is grounded in the provided context

Respond only with JSON: {{"score": <0-10>, "reason": "<one sentence>"}}"""


class FaithfulnessScorer(Scorer):
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


__all__ = ["FaithfulnessScorer"]
