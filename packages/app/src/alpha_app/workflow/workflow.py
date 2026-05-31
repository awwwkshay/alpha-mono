from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from alpha_core.contracts.executable import Executable
from alpha_core.log import logger
from alpha_core.schemas.app_context import AppContext
from alpha_core.schemas.workflow_config import (
    ConditionalWorkflowStepConfig,
    ParallelWorkflowStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)

WorkflowStepConfig.model_rebuild()
ParallelWorkflowStepConfig.model_rebuild()
ConditionalWorkflowStepConfig.model_rebuild()
WorkflowConfig.model_rebuild()


def _format_field_errors(error: ValidationError, schema: type[BaseModel]) -> str:
    lines = []
    for e in error.errors():
        if not e["loc"]:
            continue
        field_name = str(e["loc"][0])
        field = schema.model_fields.get(field_name)
        expected_type = (
            field.annotation.__name__
            if field and hasattr(field.annotation, "__name__")
            else str(field.annotation)
            if field
            else "unknown"
        )
        lines.append(f"    {field_name}: {e['msg']} (expected {expected_type})")
    return "\n".join(lines)


class WorkflowStepInputError(Exception):
    def __init__(
        self, step_name: str, schema: type[BaseModel], error: ValidationError
    ) -> None:
        field_lines = _format_field_errors(error, schema)
        super().__init__(
            f"Step '{step_name}' received invalid input for '{schema.__name__}':\n"
            f"{field_lines}\n"
            f"  Hint: make sure the previous step outputs these fields."
        )


class WorkflowStepOutputError(Exception):
    def __init__(
        self, step_name: str, schema: type[BaseModel], error: ValidationError
    ) -> None:
        field_lines = _format_field_errors(error, schema)
        super().__init__(
            f"Step '{step_name}' returned invalid output for '{schema.__name__}':\n"
            f"{field_lines}"
        )


class WorkflowBranchError(Exception):
    def __init__(self, step_name: str, branch_key: str, available: list[str]) -> None:
        super().__init__(
            f"Step '{step_name}': condition returned unknown branch '{branch_key}'. "
            f"Available: {available}"
        )


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)
_T = TypeVar("_T", bound=BaseModel)


def _coerce(data: Any, schema: type[_T]) -> _T:
    return schema.model_validate(
        data
        if isinstance(data, dict)
        else data.model_dump()
        if hasattr(data, "model_dump")
        else data
    )


class WorkflowStep(Executable[InputT, OutputT]):
    def __init__(self, *, config: WorkflowStepConfig[InputT, OutputT]) -> None:
        self.config = config
        self.input_schema = config.input_schema
        self.output_schema = config.output_schema

    @classmethod
    def create(
        cls, *, config: WorkflowStepConfig[InputT, OutputT]
    ) -> WorkflowStep[InputT, OutputT]:
        return cls(config=config)

    async def execute(self, input_data: Any, context: AppContext) -> OutputT:
        tracer = trace.get_tracer(__name__)
        logger.debug(f"Executing step '{self.config.name}'")
        with tracer.start_as_current_span(
            f"WorkflowStep.execute/{self.config.name}",
            attributes={"step_name": self.config.name, "step_type": "WorkflowStep"},
        ):
            try:
                validated_input = _coerce(input_data, self.config.input_schema)
            except ValidationError as e:
                raise WorkflowStepInputError(
                    self.config.name, self.config.input_schema, e
                ) from e

            result = await self.config.execute(validated_input, context)

            try:
                return _coerce(result, self.config.output_schema)
            except ValidationError as e:
                raise WorkflowStepOutputError(
                    self.config.name, self.config.output_schema, e
                ) from e


class ParallelWorkflowStep(Executable[InputT, OutputT]):
    """Runs all branches concurrently with the same input and merges their outputs."""

    def __init__(self, *, config: ParallelWorkflowStepConfig[InputT, OutputT]) -> None:
        self.config = config
        self.input_schema = config.input_schema
        self.output_schema = config.output_schema
        self.branches = {
            branch_id: WorkflowStep(config=branch_config)
            for branch_id, branch_config in config.branches.items()
        }

    async def execute(self, input_data: Any, context: AppContext) -> OutputT:
        tracer = trace.get_tracer(__name__)
        logger.debug(f"Executing parallel step '{self.config.name}'")
        with tracer.start_as_current_span(
            f"ParallelWorkflowStep.execute/{self.config.name}",
            attributes={
                "step_name": self.config.name,
                "step_type": "ParallelWorkflowStep",
            },
        ):
            results = await asyncio.gather(
                *[
                    branch.execute(input_data, context)
                    for branch in self.branches.values()
                ]
            )
            merged: dict = {}
            for result in results:
                merged.update(
                    result.model_dump() if hasattr(result, "model_dump") else result
                )
            try:
                return self.config.output_schema.model_validate(merged)
            except ValidationError as e:
                raise WorkflowStepOutputError(
                    self.config.name, self.config.output_schema, e
                ) from e


class ConditionalWorkflowStep(Executable[InputT, OutputT]):
    """Executes exactly one branch based on the return value of the condition function."""

    def __init__(
        self, *, config: ConditionalWorkflowStepConfig[InputT, OutputT]
    ) -> None:
        self.config = config
        self.input_schema = config.input_schema
        self.output_schema = config.output_schema
        self.branches = {
            branch_id: WorkflowStep(config=branch_config)
            for branch_id, branch_config in config.branches.items()
        }

    async def execute(self, input_data: Any, context: AppContext) -> OutputT:
        tracer = trace.get_tracer(__name__)
        logger.debug(f"Executing conditional step '{self.config.name}'")
        with tracer.start_as_current_span(
            f"ConditionalWorkflowStep.execute/{self.config.name}",
            attributes={
                "step_name": self.config.name,
                "step_type": "ConditionalWorkflowStep",
            },
        ):
            try:
                validated_input = _coerce(input_data, self.config.input_schema)
            except ValidationError as e:
                raise WorkflowStepInputError(
                    self.config.name, self.config.input_schema, e
                ) from e

            branch_key = self.config.condition(validated_input, context)
            if branch_key not in self.branches:
                raise WorkflowBranchError(
                    self.config.name, branch_key, list(self.branches.keys())
                )
            return await self.branches[branch_key].execute(input_data, context)


class Workflow(Executable[InputT, OutputT]):
    def __init__(self, *, config: WorkflowConfig[InputT, OutputT]) -> None:
        self.config = config
        self.input_schema = config.input_schema
        self.output_schema = config.output_schema
        self.steps: dict[str, Executable[Any, Any]] = {}
        for step_id, step_config in config.steps.items():
            if isinstance(step_config, WorkflowConfig):
                self.steps[step_id] = Workflow(config=step_config)
            elif isinstance(step_config, ParallelWorkflowStepConfig):
                self.steps[step_id] = ParallelWorkflowStep(config=step_config)
            elif isinstance(step_config, ConditionalWorkflowStepConfig):
                self.steps[step_id] = ConditionalWorkflowStep(config=step_config)
            else:
                self.steps[step_id] = WorkflowStep(config=step_config)

    @classmethod
    def create(
        cls, *, config: WorkflowConfig[InputT, OutputT]
    ) -> Workflow[InputT, OutputT]:
        return cls(config=config)

    async def execute(self, input_data: Any, context: AppContext) -> Any:
        tracer = trace.get_tracer(__name__)
        logger.info(f"Starting execution of workflow '{self.config.name}'")
        with tracer.start_as_current_span(
            f"Workflow.execute/{self.config.name}",
            attributes={"workflow_name": self.config.name},
        ):
            current_data: Any = input_data
            for step in self.steps.values():
                current_data = await step.execute(current_data, context)
            logger.info(f"Finished execution of workflow '{self.config.name}'")
            return current_data


__all__ = [
    "ConditionalWorkflowStep",
    "ParallelWorkflowStep",
    "Workflow",
    "WorkflowBranchError",
    "WorkflowStep",
    "WorkflowStepInputError",
    "WorkflowStepOutputError",
]
