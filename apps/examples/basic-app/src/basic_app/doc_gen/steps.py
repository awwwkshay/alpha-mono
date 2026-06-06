from __future__ import annotations

from pydantic import BaseModel

from clay_core import AppContext

from basic_app.doc_gen.schemas import (
    AnalysisDraft,
    ApiSurfaceOut,
    ComplexityOut,
    DocGenInput,
    DocOutput,
    FileContent,
    PurposeOut,
)


class _ExtractApiResult(BaseModel):
    public_functions: list[str]
    public_classes: list[str]


async def read_source_file(input: DocGenInput, context: AppContext) -> FileContent:
    agent = context.agents["reader"]
    agent_ctx = context.agent_contexts.get("reader", context)
    source = await agent.generate_async(
        f"Read the file at path: {input.file_path}",
        agent_ctx,
    )
    return FileContent(file_path=input.file_path, source=source.strip())


async def analyze_purpose(input: FileContent, context: AppContext) -> PurposeOut:
    agent = context.agents["purpose_analyzer"]
    return await agent.generate_structured_async(
        f"Analyze this Python code:\n\n{input.source}",
        context,
        PurposeOut,
    )


async def extract_api_surface(input: FileContent, context: AppContext) -> ApiSurfaceOut:
    agent = context.agents["api_surface"]
    result = await agent.generate_structured_async(
        f"Extract the public API from this Python code:\n\n{input.source}",
        context,
        _ExtractApiResult,
    )
    return ApiSurfaceOut(
        public_functions=result.public_functions,
        public_classes=result.public_classes,
        file_path=input.file_path,
        source=input.source,
    )


async def score_complexity(input: FileContent, context: AppContext) -> ComplexityOut:
    agent = context.agents["complexity_scorer"]
    return await agent.generate_structured_async(
        f"Score the complexity of this Python code:\n\n{input.source}",
        context,
        ComplexityOut,
    )


def route_by_complexity(input: AnalysisDraft, _context: AppContext) -> str:
    return "full" if input.complexity_score >= 6 else "concise"


async def write_full_doc(input: AnalysisDraft, context: AppContext) -> DocOutput:
    agent = context.agents["full_doc_writer"]
    prompt = (
        f"Write comprehensive documentation for this Python module.\n\n"
        f"File: {input.file_path}\n"
        f"Purpose: {input.purpose}\n"
        f"Type: {input.module_type}\n"
        f"Public functions: {', '.join(input.public_functions) or 'none'}\n"
        f"Public classes: {', '.join(input.public_classes) or 'none'}\n"
        f"Complexity: {input.complexity_level} (score: {input.complexity_score}/10)\n\n"
        f"Source:\n{input.source}"
    )
    documentation = await agent.generate_async(prompt, context)
    return DocOutput(file_path=input.file_path, documentation=documentation.strip())


async def write_concise_doc(input: AnalysisDraft, context: AppContext) -> DocOutput:
    agent = context.agents["concise_doc_writer"]
    prompt = (
        f"Write a concise summary for this Python module.\n\n"
        f"File: {input.file_path}\n"
        f"Purpose: {input.purpose}\n"
        f"Type: {input.module_type}\n"
        f"Public functions: {', '.join(input.public_functions) or 'none'}\n"
        f"Public classes: {', '.join(input.public_classes) or 'none'}\n"
    )
    documentation = await agent.generate_async(prompt, context)
    return DocOutput(file_path=input.file_path, documentation=documentation.strip())


__all__ = [
    "analyze_purpose",
    "extract_api_surface",
    "read_source_file",
    "route_by_complexity",
    "score_complexity",
    "write_concise_doc",
    "write_full_doc",
]
