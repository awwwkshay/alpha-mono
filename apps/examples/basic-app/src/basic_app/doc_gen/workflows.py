from __future__ import annotations

from clay_core import (
    ConditionalWorkflowStepConfig,
    ParallelWorkflowStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)

from basic_app.doc_gen.schemas import (
    AnalysisDraft,
    ApiSurfaceOut,
    ComplexityOut,
    DocGenInput,
    DocOutput,
    FileContent,
    PurposeOut,
)
from basic_app.doc_gen.steps import (
    analyze_purpose,
    extract_api_surface,
    read_source_file,
    route_by_complexity,
    score_complexity,
    write_concise_doc,
    write_full_doc,
)

DOC_GEN_WORKFLOW: WorkflowConfig = WorkflowConfig.create(
    name="Documentation Generator",
    input_schema=DocGenInput,
    output_schema=DocOutput,
    steps={
        "read": WorkflowStepConfig.create(
            name="Read Source File",
            input_schema=DocGenInput,
            output_schema=FileContent,
            execute=read_source_file,
        ),
        "analyze": ParallelWorkflowStepConfig.create(
            name="Parallel Analysis",
            input_schema=FileContent,
            output_schema=AnalysisDraft,
            branches={
                "purpose": WorkflowStepConfig.create(
                    name="Analyze Purpose",
                    input_schema=FileContent,
                    output_schema=PurposeOut,
                    execute=analyze_purpose,
                ),
                "api_surface": WorkflowStepConfig.create(
                    name="Extract API Surface",
                    input_schema=FileContent,
                    output_schema=ApiSurfaceOut,
                    execute=extract_api_surface,
                ),
                "complexity": WorkflowStepConfig.create(
                    name="Score Complexity",
                    input_schema=FileContent,
                    output_schema=ComplexityOut,
                    execute=score_complexity,
                ),
            },
        ),
        "write": ConditionalWorkflowStepConfig.create(
            name="Write Documentation",
            input_schema=AnalysisDraft,
            output_schema=DocOutput,
            condition=route_by_complexity,
            branches={
                "full": WorkflowStepConfig.create(
                    name="Full Documentation",
                    input_schema=AnalysisDraft,
                    output_schema=DocOutput,
                    execute=write_full_doc,
                ),
                "concise": WorkflowStepConfig.create(
                    name="Concise Summary",
                    input_schema=AnalysisDraft,
                    output_schema=DocOutput,
                    execute=write_concise_doc,
                ),
            },
        ),
    },
)

__all__ = ["DOC_GEN_WORKFLOW"]
