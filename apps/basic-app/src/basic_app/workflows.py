from __future__ import annotations

from alpha_core.schemas.workflow_config import (
    ConditionalWorkflowStepConfig,
    ParallelWorkflowStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)

from basic_app.schemas import (
    CodeReview,
    CodeSummary,
    PerformanceOut,
    ReviewDraft,
    ReviewReport,
    SecurityOut,
    StyleOut,
)
from basic_app.steps import (
    parse_code,
    performance_review,
    route_by_severity,
    security_review,
    standard_report,
    style_review,
    urgent_report,
)

REVIEW_WORKFLOW: WorkflowConfig = WorkflowConfig.create(
    name="Code Review",
    input_schema=CodeReview,
    output_schema=ReviewReport,
    steps={
        "parse": WorkflowStepConfig.create(
            name="Parse Code",
            input_schema=CodeReview,
            output_schema=CodeSummary,
            execute=parse_code,
        ),
        "analyze": ParallelWorkflowStepConfig.create(
            name="Parallel Review",
            input_schema=CodeSummary,
            output_schema=ReviewDraft,
            branches={
                "security": WorkflowStepConfig.create(
                    name="Security",
                    input_schema=CodeSummary,
                    output_schema=SecurityOut,
                    execute=security_review,
                ),
                "performance": WorkflowStepConfig.create(
                    name="Performance",
                    input_schema=CodeSummary,
                    output_schema=PerformanceOut,
                    execute=performance_review,
                ),
                "style": WorkflowStepConfig.create(
                    name="Style",
                    input_schema=CodeSummary,
                    output_schema=StyleOut,
                    execute=style_review,
                ),
            },
        ),
        "report": ConditionalWorkflowStepConfig.create(
            name="Write Report",
            input_schema=ReviewDraft,
            output_schema=ReviewReport,
            condition=route_by_severity,
            branches={
                "urgent": WorkflowStepConfig.create(
                    name="Urgent Report",
                    input_schema=ReviewDraft,
                    output_schema=ReviewReport,
                    execute=urgent_report,
                ),
                "standard": WorkflowStepConfig.create(
                    name="Standard Report",
                    input_schema=ReviewDraft,
                    output_schema=ReviewReport,
                    execute=standard_report,
                ),
            },
        ),
    },
)

__all__ = ["REVIEW_WORKFLOW"]
