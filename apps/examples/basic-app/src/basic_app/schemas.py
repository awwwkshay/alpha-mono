from __future__ import annotations

from pydantic import BaseModel


class CodeReview(BaseModel):
    code: str
    language: str


class CodeSummary(BaseModel):
    code: str
    language: str
    purpose: str
    patterns: list[str]


class SecurityOut(BaseModel):
    security_issues: str
    severity: str


class PerformanceOut(BaseModel):
    performance_issues: str


class StyleOut(BaseModel):
    style_issues: str


class ReviewDraft(BaseModel):
    security_issues: str
    severity: str
    performance_issues: str
    style_issues: str


class ReviewReport(BaseModel):
    verdict: str
    priority_issues: list[str]
    recommendations: list[str]


__all__ = [
    "CodeReview",
    "CodeSummary",
    "PerformanceOut",
    "ReviewDraft",
    "ReviewReport",
    "SecurityOut",
    "StyleOut",
]
