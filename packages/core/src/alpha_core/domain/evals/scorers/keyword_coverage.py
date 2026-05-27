from __future__ import annotations

from alpha_core.domain.evals.scorer import Scorer, ScorerResult


class KeywordCoverageScorer(Scorer):
    """Rule-based scorer: fraction of required keywords present in the output."""

    def __init__(self, *, keywords: list[str], case_sensitive: bool = False) -> None:
        self._keywords = keywords
        self._case_sensitive = case_sensitive

    async def score(self, input: str, output: str) -> ScorerResult:  # noqa: ARG002
        if not self._keywords:
            return ScorerResult(score=1.0, reason="No keywords configured")

        check_output = output if self._case_sensitive else output.lower()
        found = [
            kw
            for kw in self._keywords
            if (kw if self._case_sensitive else kw.lower()) in check_output
        ]
        coverage = len(found) / len(self._keywords)
        missing = [kw for kw in self._keywords if kw not in found]
        reason = f"Found {len(found)}/{len(self._keywords)} keywords" + (
            f"; missing: {', '.join(missing)}" if missing else ""
        )
        return ScorerResult(score=coverage, reason=reason)


__all__ = ["KeywordCoverageScorer"]
