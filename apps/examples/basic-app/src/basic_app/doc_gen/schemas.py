from __future__ import annotations

from pydantic import BaseModel


class DocGenInput(BaseModel):
    file_path: str


class FileContent(BaseModel):
    file_path: str
    source: str


class PurposeOut(BaseModel):
    purpose: str
    module_type: str


class ApiSurfaceOut(BaseModel):
    public_functions: list[str]
    public_classes: list[str]
    file_path: str
    source: str


class ComplexityOut(BaseModel):
    complexity_level: str
    complexity_score: int


class AnalysisDraft(BaseModel):
    purpose: str
    module_type: str
    public_functions: list[str]
    public_classes: list[str]
    file_path: str
    source: str
    complexity_level: str
    complexity_score: int


class DocOutput(BaseModel):
    file_path: str
    documentation: str


__all__ = [
    "AnalysisDraft",
    "ApiSurfaceOut",
    "ComplexityOut",
    "DocGenInput",
    "DocOutput",
    "FileContent",
    "PurposeOut",
]
