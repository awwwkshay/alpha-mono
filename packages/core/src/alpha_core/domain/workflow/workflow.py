import asyncio
from collections.abc import Awaitable
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ValidationError

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


class WorkflowStep(Generic[InputT, OutputT]):
    def __init__(self, *, config: WorkflowStepConfig[InputT, OutputT]):
        self.config = config
        self.execute = self.prepare_execute()

    @classmethod
    def create(
        cls, *, config: WorkflowStepConfig[InputT, OutputT]
    ) -> WorkflowStep[InputT, OutputT]:
        return cls(config=config)

    def prepare_execute(self) -> Callable[[Any, AppContext], Awaitable[BaseModel]]:
        async def _execute(input_data: Any, context: AppContext) -> BaseModel:
            try:
                # model_validate can accept dicts or model instances
                validated_input = self.config.input_schema.model_validate(
                    input_data
                    if isinstance(input_data, dict)
                    else input_data.model_dump()
                    if hasattr(input_data, "model_dump")
                    else input_data
                )
            except ValidationError as e:
                raise WorkflowStepInputError(
                    self.config.name, self.config.input_schema, e
                ) from e

            result = await self.config.execute(validated_input, context)

            try:
                # result is an instance of output_schema already or dict
                return self.config.output_schema.model_validate(
                    result
                    if isinstance(result, dict)
                    else result.model_dump()
                    if hasattr(result, "model_dump")
                    else result
                )
            except ValidationError as e:
                raise WorkflowStepOutputError(
                    self.config.name, self.config.output_schema, e
                ) from e

        return _execute


class ParallelWorkflowStep(Generic[InputT, OutputT]):
    """Runs all branches concurrently with the same input and merges their outputs."""

    def __init__(self, *, config: ParallelWorkflowStepConfig[InputT, OutputT]):
        self.config = config
        self.branches = {
            branch_id: WorkflowStep(config=branch_config)
            for branch_id, branch_config in config.branches.items()
        }
        self.execute = self.prepare_execute()

    def prepare_execute(self) -> Callable[[Any, AppContext], Awaitable[BaseModel]]:
        async def _execute(input_data: Any, context: AppContext) -> BaseModel:
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

        return _execute


class ConditionalWorkflowStep(Generic[InputT, OutputT]):
    """Executes exactly one branch based on the return value of the
    condition function."""

    def __init__(self, *, config: ConditionalWorkflowStepConfig[InputT, OutputT]):
        self.config = config
        self.branches = {
            branch_id: WorkflowStep(config=branch_config)
            for branch_id, branch_config in config.branches.items()
        }
        self.execute = self.prepare_execute()

    def prepare_execute(self) -> Callable[[Any, AppContext], Awaitable[BaseModel]]:
        async def _execute(input_data: Any, context: AppContext) -> BaseModel:
            try:
                validated_input = self.config.input_schema.model_validate(
                    input_data
                    if isinstance(input_data, dict)
                    else input_data.model_dump()
                    if hasattr(input_data, "model_dump")
                    else input_data
                )
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

        return _execute


class Workflow(Generic[InputT, OutputT]):
    def __init__(self, *, config: WorkflowConfig[InputT, OutputT]):
        self.config = config
        self.steps: dict[
            str, WorkflowStep | ParallelWorkflowStep | ConditionalWorkflowStep
        ] = {}
        for step_id, step_config in config.steps.items():
            if isinstance(step_config, ParallelWorkflowStepConfig):
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
        current_data: Any = input_data
        for step in self.steps.values():
            current_data = await step.execute(current_data, context)
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
