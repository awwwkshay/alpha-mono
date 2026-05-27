from __future__ import annotations

from alpha_core.schemas.app_context import AppContext

from basic_app.doc_gen.schemas import (
    AnalysisDraft,
    ApiSurfaceOut,
    ComplexityOut,
    DocGenInput,
    DocOutput,
    FileContent,
    PurposeOut,
)


async def read_source_file(input: DocGenInput, context: AppContext) -> FileContent:
    agent = context.agents["reader"]
    source = await agent.generate_async(
        f"Read the file at path: {input.file_path}",
        context,
    )
    return FileContent(file_path=input.file_path, source=source.strip())


async def analyze_purpose(input: FileContent, context: AppContext) -> PurposeOut:
    agent = context.agents["purpose_analyzer"]
    response = await agent.generate_async(
        f"Analyze this Python code:\n\n{input.source}",
        context,
    )
    purpose, module_type = "", "utility"
    for line in response.splitlines():
        if line.startswith("PURPOSE:"):
            purpose = line.removeprefix("PURPOSE:").strip()
        elif line.startswith("TYPE:"):
            raw = line.removeprefix("TYPE:").strip().lower()
            module_type = (
                raw
                if raw
                in ("utility", "domain_model", "service", "config", "workflow", "test")
                else "utility"
            )
    return PurposeOut(purpose=purpose, module_type=module_type)


async def extract_api_surface(input: FileContent, context: AppContext) -> ApiSurfaceOut:
    agent = context.agents["api_surface"]
    response = await agent.generate_async(
        f"Extract the public API from this Python code:\n\n{input.source}",
        context,
    )
    functions: list[str] = []
    classes: list[str] = []
    for line in response.splitlines():
        if line.startswith("FUNCTIONS:"):
            raw = line.removeprefix("FUNCTIONS:").strip()
            if raw.lower() != "none":
                functions = [f.strip() for f in raw.split(",") if f.strip()]
        elif line.startswith("CLASSES:"):
            raw = line.removeprefix("CLASSES:").strip()
            if raw.lower() != "none":
                classes = [c.strip() for c in raw.split(",") if c.strip()]
    return ApiSurfaceOut(
        public_functions=functions,
        public_classes=classes,
        file_path=input.file_path,
        source=input.source,
    )


async def score_complexity(input: FileContent, context: AppContext) -> ComplexityOut:
    agent = context.agents["complexity_scorer"]
    response = await agent.generate_async(
        f"Score the complexity of this Python code:\n\n{input.source}",
        context,
    )
    level, score = "simple", 3
    for line in response.splitlines():
        if line.startswith("LEVEL:"):
            raw = line.removeprefix("LEVEL:").strip().lower()
            level = raw if raw in ("simple", "complex") else "simple"
        elif line.startswith("SCORE:"):
            try:
                score = int(line.removeprefix("SCORE:").strip())
            except ValueError:
                pass
    return ComplexityOut(complexity_level=level, complexity_score=score)


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
