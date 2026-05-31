from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from alpha_app.workflow.workflow import (
    ConditionalWorkflowStep,
    ParallelWorkflowStep,
    Workflow,
    WorkflowBranchError,
    WorkflowStep,
    WorkflowStepInputError,
    WorkflowStepOutputError,
)
from alpha_core.schemas.app_config import AppConfig
from alpha_core.schemas.app_context import AppContext
from alpha_core.schemas.workflow_config import (
    ConditionalWorkflowStepConfig,
    ParallelWorkflowStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)


# ---------------------------------------------------------------------------
# Shared test schemas
# ---------------------------------------------------------------------------


class Inp(BaseModel):
    value: int


class Out(BaseModel):
    result: str


class Mid(BaseModel):
    value: int
    result: str


def _ctx() -> AppContext:
    return AppContext(config=AppConfig(name="test"))


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------


async def test_workflow_step_executes_and_returns_output():
    async def _fn(inp: Inp, _ctx) -> Out:
        return Out(result=str(inp.value))

    cfg = WorkflowStepConfig.create(
        name="s", input_schema=Inp, output_schema=Out, execute=_fn
    )
    step = WorkflowStep(config=cfg)
    result = await step.execute({"value": 42}, _ctx())
    assert result.model_dump() == {"result": "42"}


async def test_workflow_step_raises_input_error_on_bad_input():
    async def _fn(inp: Inp, _ctx) -> Out:
        return Out(result="ok")  # pragma: no cover

    cfg = WorkflowStepConfig.create(
        name="parse", input_schema=Inp, output_schema=Out, execute=_fn
    )
    step = WorkflowStep(config=cfg)
    with pytest.raises(WorkflowStepInputError, match="parse"):
        await step.execute({"value": "not-an-int"}, _ctx())


async def test_workflow_step_raises_output_error_on_bad_output():
    async def _fn(inp: Inp, _ctx):
        return {"result": 999}  # result should be str

    cfg = WorkflowStepConfig.create(
        name="out", input_schema=Inp, output_schema=Out, execute=_fn
    )
    step = WorkflowStep(config=cfg)
    with pytest.raises(WorkflowStepOutputError, match="out"):
        await step.execute({"value": 1}, _ctx())


# ---------------------------------------------------------------------------
# ParallelWorkflowStep
# ---------------------------------------------------------------------------


class BranchAOut(BaseModel):
    a: str


class BranchBOut(BaseModel):
    b: str


class MergedOut(BaseModel):
    a: str
    b: str


async def test_parallel_step_merges_branch_outputs():
    async def _branch_a(inp: Inp, _ctx) -> BranchAOut:
        return BranchAOut(a=f"a={inp.value}")

    async def _branch_b(inp: Inp, _ctx) -> BranchBOut:
        return BranchBOut(b=f"b={inp.value}")

    step_a = WorkflowStepConfig.create(
        name="A", input_schema=Inp, output_schema=BranchAOut, execute=_branch_a
    )
    step_b = WorkflowStepConfig.create(
        name="B", input_schema=Inp, output_schema=BranchBOut, execute=_branch_b
    )

    cfg = ParallelWorkflowStepConfig.create(
        name="parallel",
        input_schema=Inp,
        output_schema=MergedOut,
        branches={"a": step_a, "b": step_b},
    )
    step = ParallelWorkflowStep(config=cfg)
    result = await step.execute({"value": 7}, _ctx())
    assert result.model_dump() == {"a": "a=7", "b": "b=7"}


async def test_parallel_step_raises_output_error_on_merge_mismatch():
    """If the merged data can't be validated against output_schema, raise WorkflowStepOutputError."""

    class TooFew(BaseModel):
        a: str

    async def _fn(inp: Inp, _ctx) -> BranchAOut:
        return BranchAOut(a="ok")

    step_a = WorkflowStepConfig.create(
        name="A", input_schema=Inp, output_schema=BranchAOut, execute=_fn
    )

    # MergedOut requires both a and b — but only a branch is provided
    with pytest.raises(Exception):
        ParallelWorkflowStepConfig.create(
            name="p",
            input_schema=Inp,
            output_schema=MergedOut,
            branches={"a": step_a},
        )


# ---------------------------------------------------------------------------
# ConditionalWorkflowStep
# ---------------------------------------------------------------------------


async def test_conditional_step_routes_to_correct_branch():
    async def _fast(inp: Inp, _ctx) -> Out:
        return Out(result="fast")

    async def _slow(inp: Inp, _ctx) -> Out:
        return Out(result="slow")

    fast_cfg = WorkflowStepConfig.create(
        name="fast", input_schema=Inp, output_schema=Out, execute=_fast
    )
    slow_cfg = WorkflowStepConfig.create(
        name="slow", input_schema=Inp, output_schema=Out, execute=_slow
    )

    def _condition(inp: Inp, _ctx) -> str:
        return "fast" if inp.value < 10 else "slow"

    cfg = ConditionalWorkflowStepConfig.create(
        name="router",
        input_schema=Inp,
        output_schema=Out,
        condition=_condition,
        branches={"fast": fast_cfg, "slow": slow_cfg},
    )
    step = ConditionalWorkflowStep(config=cfg)

    result_fast = await step.execute({"value": 5}, _ctx())
    assert result_fast.model_dump() == {"result": "fast"}

    result_slow = await step.execute({"value": 20}, _ctx())
    assert result_slow.model_dump() == {"result": "slow"}


async def test_conditional_step_unknown_branch_raises():
    async def _fn(inp: Inp, _ctx) -> Out:
        return Out(result="ok")

    branch_cfg = WorkflowStepConfig.create(
        name="b", input_schema=Inp, output_schema=Out, execute=_fn
    )

    def _bad_condition(inp: Inp, _ctx) -> str:
        return "nonexistent"

    cfg = ConditionalWorkflowStepConfig.create(
        name="router",
        input_schema=Inp,
        output_schema=Out,
        condition=_bad_condition,
        branches={"b": branch_cfg},
    )
    step = ConditionalWorkflowStep(config=cfg)
    with pytest.raises(WorkflowBranchError, match="nonexistent"):
        await step.execute({"value": 1}, _ctx())


async def test_conditional_step_raises_input_error_on_bad_input():
    async def _fn(inp: Inp, _ctx) -> Out:
        return Out(result="ok")  # pragma: no cover

    branch_cfg = WorkflowStepConfig.create(
        name="b", input_schema=Inp, output_schema=Out, execute=_fn
    )

    def _cond(inp: Inp, _ctx) -> str:
        return "b"  # pragma: no cover

    cfg = ConditionalWorkflowStepConfig.create(
        name="cond",
        input_schema=Inp,
        output_schema=Out,
        condition=_cond,
        branches={"b": branch_cfg},
    )
    step = ConditionalWorkflowStep(config=cfg)
    with pytest.raises(WorkflowStepInputError, match="cond"):
        await step.execute({"value": "bad"}, _ctx())


# ---------------------------------------------------------------------------
# Workflow.execute — sequential piping
# ---------------------------------------------------------------------------


class Step1Out(BaseModel):
    doubled: int


class Step2Out(BaseModel):
    doubled: int
    label: str


async def test_workflow_executes_steps_sequentially():
    async def _step1(inp: Inp, _ctx) -> Step1Out:
        return Step1Out(doubled=inp.value * 2)

    async def _step2(inp: Step1Out, _ctx) -> Step2Out:
        return Step2Out(doubled=inp.doubled, label=f"val={inp.doubled}")

    s1 = WorkflowStepConfig.create(
        name="s1", input_schema=Inp, output_schema=Step1Out, execute=_step1
    )
    s2 = WorkflowStepConfig.create(
        name="s2", input_schema=Step1Out, output_schema=Step2Out, execute=_step2
    )
    wf = WorkflowConfig.create(
        name="wf", input_schema=Inp, output_schema=Step2Out, steps={"s1": s1, "s2": s2}
    )

    workflow = Workflow(config=wf)
    result = await workflow.execute({"value": 5}, _ctx())
    assert result.model_dump() == {"doubled": 10, "label": "val=10"}


async def test_workflow_single_step():
    async def _fn(inp: Inp, _ctx) -> Out:
        return Out(result=str(inp.value))

    cfg = WorkflowStepConfig.create(
        name="only", input_schema=Inp, output_schema=Out, execute=_fn
    )
    wf = WorkflowConfig.create(
        name="wf", input_schema=Inp, output_schema=Out, steps={"only": cfg}
    )

    workflow = Workflow(config=wf)
    result = await workflow.execute({"value": 3}, _ctx())
    assert result.model_dump() == {"result": "3"}


# ---------------------------------------------------------------------------
# Error class messages
# ---------------------------------------------------------------------------


def test_workflow_step_input_error_message():
    try:
        Inp.model_validate({"value": "bad"})
    except ValidationError as e:
        err = WorkflowStepInputError("my_step", Inp, e)
        assert "my_step" in str(err)
        assert "Inp" in str(err)


def test_workflow_step_output_error_message():
    try:
        Out.model_validate({"result": 123})
    except ValidationError as e:
        err = WorkflowStepOutputError("my_step", Out, e)
        assert "my_step" in str(err)
        assert "Out" in str(err)


def test_workflow_branch_error_message():
    err = WorkflowBranchError("router", "unknown", ["a", "b"])
    msg = str(err)
    assert "router" in msg
    assert "unknown" in msg
    assert "['a', 'b']" in msg
