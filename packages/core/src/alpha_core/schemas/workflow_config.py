from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

if TYPE_CHECKING:
    from alpha_core.schemas.app_context import AppContext


class WorkflowConfigError(Exception):
    pass


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


def _schema_fields(schema: type[BaseModel]) -> dict[str, type]:
    return {name: info.annotation for name, info in schema.model_fields.items()}


def _diff(expected: type[BaseModel], actual: type[BaseModel]) -> list[str]:
    """Return errors where `actual` does not exactly match `expected`."""
    expected_fields = _schema_fields(expected)
    actual_fields = _schema_fields(actual)
    errors = []
    for field, typ in expected_fields.items():
        if field not in actual_fields:
            errors.append(f"    '{field}: {typ}' is missing")
        elif actual_fields[field] != typ:
            errors.append(f"    '{field}': expected {typ}, got {actual_fields[field]}")
    for field in actual_fields:
        if field not in expected_fields:
            errors.append(f"    '{field}' is unexpected (not in {expected.__name__})")
    return errors


def _build_config_error(e: ValidationError) -> WorkflowConfigError:
    messages = []
    for err in e.errors():
        msg = err["msg"]
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        messages.append(msg)
    return WorkflowConfigError("\n".join(messages))


class WorkflowStepConfig(BaseModel, Generic[InputT, OutputT]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the workflow step")
    description: str | None = Field(default=None)
    input_schema: type[InputT] = Field(...)
    output_schema: type[OutputT] = Field(...)
    execute: Callable[[InputT, AppContext], Awaitable[OutputT]] = Field(...)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        execute: Callable[[InputT, AppContext], Awaitable[OutputT]],
        description: str | None = None,
    ) -> WorkflowStepConfig[InputT, OutputT]:
        from alpha_core.schemas.app_context import AppContext  # noqa: F401

        cls.model_rebuild()
        return cls(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            execute=execute,
        )


class ParallelWorkflowStepConfig(BaseModel, Generic[InputT, OutputT]):
    """
    Fans the same input out to all branches concurrently and merges their outputs.
    Branches must have non-overlapping output fields. The step's output_schema must
    contain exactly the union of all branch output fields.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(...)
    description: str | None = Field(default=None)
    input_schema: type[InputT] = Field(...)
    output_schema: type[OutputT] = Field(...)
    branches: dict[str, WorkflowStepConfig] = Field(...)

    @model_validator(mode="after")
    def validate_branches(self) -> ParallelWorkflowStepConfig[InputT, OutputT]:
        branch_output_fields: dict[str, tuple[type, str]] = {}

        for branch_id, branch in self.branches.items():
            errors = _diff(self.input_schema, branch.input_schema)
            if errors:
                raise ValueError(
                    f"Branch '{branch_id}' input"
                    f" '{branch.input_schema.__name__}' does not match"
                    f" parallel step input '{self.input_schema.__name__}':\n"
                    + "\n".join(errors)
                )

            for field, typ in _schema_fields(branch.output_schema).items():
                if field in branch_output_fields:
                    existing = branch_output_fields[field][1]
                    raise ValueError(
                        f"Output field '{field}' appears in both"
                        f" branch '{existing}' and '{branch_id}' "
                        f"— parallel branches must have non-overlapping output fields"
                    )
                branch_output_fields[field] = (typ, branch_id)

        errors = self._validate_output_fields(branch_output_fields)
        if errors:
            raise ValueError(
                f"Parallel step '{self.name}' output"
                f" '{self.output_schema.__name__}' does not match"
                f" combined branch outputs:\n" + "\n".join(errors)
            )

        return self

    def _validate_output_fields(
        self,
        branch_output_fields: dict[str, tuple[type, str]],
    ) -> list[str]:
        output_fields = _schema_fields(self.output_schema)
        errors = []
        for field, (typ, branch_id) in branch_output_fields.items():
            if field not in output_fields:
                errors.append(
                    f"    '{field}: {typ}' (from branch"
                    f" '{branch_id}') is missing from output schema"
                )
            elif output_fields[field] != typ:
                errors.append(
                    f"    '{field}': expected {typ}"
                    f" (from branch '{branch_id}'),"
                    f" got {output_fields[field]}"
                )
        for field in output_fields:
            if field not in branch_output_fields:
                errors.append(
                    f"    '{field}' in output schema is not produced by any branch"
                )
        return errors

    @classmethod
    def create(
        cls,
        *,
        name: str,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        branches: dict[str, WorkflowStepConfig],
        description: str | None = None,
    ) -> ParallelWorkflowStepConfig[InputT, OutputT]:
        from alpha_core.schemas.app_context import AppContext  # noqa: F401

        WorkflowStepConfig.model_rebuild()
        cls.model_rebuild()
        try:
            return cls(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                branches=branches,
            )
        except ValidationError as e:
            raise _build_config_error(e) from None


class ConditionalWorkflowStepConfig(BaseModel, Generic[InputT, OutputT]):
    """
    Routes to exactly one branch based on the return value of `condition`.
    All branches must share the same input and output schema as the step itself.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(...)
    description: str | None = Field(default=None)
    input_schema: type[InputT] = Field(...)
    output_schema: type[OutputT] = Field(...)
    condition: Callable[[InputT, AppContext], str] = Field(
        ..., description="Returns the key of the branch to execute"
    )
    branches: dict[str, WorkflowStepConfig] = Field(...)

    @model_validator(mode="after")
    def validate_branches(self) -> ConditionalWorkflowStepConfig[InputT, OutputT]:
        for branch_id, branch in self.branches.items():
            errors = _diff(self.input_schema, branch.input_schema)
            if errors:
                raise ValueError(
                    f"Branch '{branch_id}' input"
                    f" '{branch.input_schema.__name__}' does not match"
                    f" conditional step input '{self.input_schema.__name__}':\n"
                    + "\n".join(errors)
                )
            errors = _diff(self.output_schema, branch.output_schema)
            if errors:
                raise ValueError(
                    f"Branch '{branch_id}' output"
                    f" '{branch.output_schema.__name__}' does not match"
                    f" conditional step output '{self.output_schema.__name__}':\n"
                    + "\n".join(errors)
                )
        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        condition: Callable[[InputT, AppContext], str],
        branches: dict[str, WorkflowStepConfig],
        description: str | None = None,
    ) -> ConditionalWorkflowStepConfig[InputT, OutputT]:
        from alpha_core.schemas.app_context import AppContext  # noqa: F401

        WorkflowStepConfig.model_rebuild()
        cls.model_rebuild()
        try:
            return cls(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                condition=condition,
                branches=branches,
            )
        except ValidationError as e:
            raise _build_config_error(e) from None


AnyStepConfig = (
    WorkflowStepConfig | ParallelWorkflowStepConfig | ConditionalWorkflowStepConfig
)


class WorkflowConfig(BaseModel, Generic[InputT, OutputT]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(...)
    description: str | None = Field(default=None)
    input_schema: type[InputT] = Field(...)
    output_schema: type[OutputT] = Field(...)
    steps: dict[str, AnyStepConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_step_chain(self) -> WorkflowConfig[InputT, OutputT]:
        steps = list(self.steps.values())
        if not steps:
            return self

        errors = _diff(steps[0].input_schema, self.input_schema)
        if errors:
            raise ValueError(
                f"Workflow input schema '{self.input_schema.__name__}'"
                f" does not match first step '{steps[0].name}'"
                f" input '{steps[0].input_schema.__name__}':\n" + "\n".join(errors)
            )

        for current, nxt in zip(steps, steps[1:]):
            errors = _diff(nxt.input_schema, current.output_schema)
            if errors:
                raise ValueError(
                    f"Step '{current.name}' output"
                    f" '{current.output_schema.__name__}' does not match"
                    f" step '{nxt.name}' input '{nxt.input_schema.__name__}':\n"
                    + "\n".join(errors)
                )

        errors = _diff(self.output_schema, steps[-1].output_schema)
        if errors:
            raise ValueError(
                f"Last step '{steps[-1].name}' output"
                f" '{steps[-1].output_schema.__name__}' does not match"
                f" workflow output schema '{self.output_schema.__name__}':\n"
                + "\n".join(errors)
            )

        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        steps: dict[str, AnyStepConfig],
        description: str | None = None,
    ) -> WorkflowConfig[InputT, OutputT]:
        from alpha_core.schemas.app_context import (
            AppContext,  # noqa: F401  # pyright: ignore[reportUnusedImport]
        )

        WorkflowStepConfig.model_rebuild()
        try:
            return cls(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                steps=steps,
            )
        except ValidationError as e:
            raise _build_config_error(e) from None


__all__ = [
    "AnyStepConfig",
    "ConditionalWorkflowStepConfig",
    "ParallelWorkflowStepConfig",
    "WorkflowConfig",
    "WorkflowConfigError",
    "WorkflowStepConfig",
]
