from __future__ import annotations

import json

from alpha_core import Scorer, ScorerResult

_PROMPT = """\
Rate how relevant the following response is to the input question.

Input: {input}
Response: {output}

Score from 0 to 10:
- 0: completely irrelevant
- 10: directly and fully answers the question

Respond only with JSON: {{"score": <0-10>, "reason": "<one sentence>"}}"""


class AnswerRelevancyScorer(Scorer):
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


__all__ = ["AnswerRelevancyScorer"]
