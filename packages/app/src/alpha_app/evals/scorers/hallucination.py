from __future__ import annotations

import json

from alpha_core import Scorer, ScorerResult

_PROMPT = """\
Detect hallucinations in the following response — factual contradictions or \
unsupported claims relative to the input.

Input: {input}
Response: {output}

Score from 0 to 10 where higher means MORE hallucination detected:
- 0: no hallucinations, all claims are accurate
- 10: severe hallucinations, many fabricated or contradictory claims

Respond only with JSON: {{"score": <0-10>, "reason": "<one sentence>"}}"""


class HallucinationScorer(Scorer):
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
        raw = float(data["score"]) / 10.0
        return ScorerResult(
            score=raw,
            reason=data.get("reason"),
            metadata={"lower_is_better": True},
        )


__all__ = ["HallucinationScorer"]
