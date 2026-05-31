"""
OpenTelemetry attribute name constants for alpha_app spans.

Organised by domain. All span attribute keys are defined here so they stay
consistent across agent, workflow, workspace, and app instrumentation.

GenAI keys follow the OpenTelemetry Semantic Conventions for GenAI systems:
https://opentelemetry.io/docs/specs/semconv/gen-ai/
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Span names
# ---------------------------------------------------------------------------

SPAN_APP_EXECUTE_WORKFLOW = "app.execute_workflow"
SPAN_AGENT_GENERATE = "agent.generate"
SPAN_AGENT_GENERATE_STREAM = "agent.generate_stream"
SPAN_AGENT_GENERATE_STRUCTURED = "agent.generate_structured"
SPAN_AGENT_GENERATE_WITH_EVALS = "agent.generate_with_evals"
SPAN_AGENT_TOOL_CALL = "agent.tool_call"
SPAN_LLM_CHAT = "gen_ai.chat"
SPAN_LLM_CHAT_STREAM = "gen_ai.chat.stream"
SPAN_WORKFLOW_EXECUTE = "workflow.execute"
SPAN_WORKFLOW_STEP_EXECUTE = "workflow.step.execute"
SPAN_WORKFLOW_STEP_PARALLEL = "workflow.step.parallel"
SPAN_WORKFLOW_STEP_CONDITIONAL = "workflow.step.conditional"
SPAN_WORKSPACE_TOOL = "workspace.tool"

# ---------------------------------------------------------------------------
# GenAI / LLM  (OTel semconv gen_ai.*)
# ---------------------------------------------------------------------------

# The AI provider / system being called (e.g. "openai", "anthropic", "litellm")
GEN_AI_SYSTEM = "gen_ai.system"

# High-level operation type: "chat", "text_completion", "embeddings", etc.
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"

# Model requested by the caller
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"

# Actual model returned in the response (may differ from requested)
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"

# Token counts from the response usage block
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"

# Thinking / reasoning tokens (Anthropic extended-thinking models)
GEN_AI_USAGE_THINKING_TOKENS = "gen_ai.usage.thinking_tokens"
GEN_AI_USAGE_CACHE_READ_TOKENS = "gen_ai.usage.cache_read_tokens"
GEN_AI_USAGE_CACHE_CREATION_TOKENS = "gen_ai.usage.cache_creation_tokens"

# Why the model stopped generating
GEN_AI_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reason"

# Whether thinking / extended reasoning was active for this call
GEN_AI_THINKING_ENABLED = "gen_ai.thinking.enabled"

# Budget tokens allocated to thinking (Anthropic claude-3-7-sonnet and later)
GEN_AI_THINKING_BUDGET_TOKENS = "gen_ai.thinking.budget_tokens"

# Temperature and sampling parameters forwarded to the model
GEN_AI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
GEN_AI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
GEN_AI_REQUEST_TOP_P = "gen_ai.request.top_p"

# ---------------------------------------------------------------------------
# LLM call (per-iteration detail)
# ---------------------------------------------------------------------------

# How many messages were in the context when this call was made
LLM_MESSAGE_COUNT = "llm.message_count"

# Which iteration of the tool-call loop this call belongs to (0-indexed)
LLM_ITERATION = "llm.iteration"

# Whether tool definitions were included in the request
LLM_HAS_TOOLS = "llm.has_tools"

# Number of tool definitions sent to the model
LLM_TOOL_DEFINITION_COUNT = "llm.tool_definition_count"

# Whether the model returned tool calls in this response
LLM_RETURNED_TOOL_CALLS = "llm.returned_tool_calls"

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

AGENT_NAME = "agent.name"
AGENT_DESCRIPTION = "agent.description"

# Character length of the user prompt
AGENT_PROMPT_LENGTH = "agent.prompt.length"

# Actual user prompt text
AGENT_PROMPT = "user.prompt"

# Character length of the final text response
AGENT_RESPONSE_LENGTH = "agent.response.length"

# Actual agent response text
AGENT_RESPONSE = "agent.response"

# Span event names for capturing actual content
EVENT_USER_MESSAGE = "gen_ai.user.message"
EVENT_ASSISTANT_MESSAGE = "gen_ai.assistant.message"
EVENT_TOOL_CALL = "gen_ai.tool.call"
EVENT_TOOL_RESULT = "gen_ai.tool.result"

# Total number of tools (functions + sub-workflows) available to the agent
AGENT_TOOL_COUNT = "agent.tool_count"

# Whether the agent has any tools at all
AGENT_HAS_TOOLS = "agent.has_tools"

# Whether scorers are configured on the agent
AGENT_HAS_SCORERS = "agent.has_scorers"

# For structured generation: the Pydantic response model class name
AGENT_RESPONSE_MODEL = "agent.response_model"

# Whether a conversation history was passed in
AGENT_HAS_HISTORY = "agent.has_history"

# Total number of LLM iterations consumed during a generate call
AGENT_TOTAL_ITERATIONS = "agent.total_iterations"

# Total number of tool calls dispatched during a generate call
AGENT_TOTAL_TOOL_CALLS = "agent.total_tool_calls"

# ---------------------------------------------------------------------------
# Agent tool dispatch
# ---------------------------------------------------------------------------

TOOL_NAME = "tool.name"

# Actual tool input arguments (JSON-serialised)
TOOL_INPUT = "tool.input"

# Actual tool output result
TOOL_OUTPUT = "tool.output"

# "function" | "workflow"
TOOL_TYPE = "tool.type"

# Character length of the serialised tool result
TOOL_RESULT_LENGTH = "tool.result.length"

# ---------------------------------------------------------------------------
# Workspace tool
# ---------------------------------------------------------------------------

WORKSPACE_NAME = "workspace.name"

# "filesystem" | "sandbox" | "skill"
WORKSPACE_TOOL_CATEGORY = "workspace.tool.category"

# True if the tool returned successfully, False if it caught an error
WORKSPACE_TOOL_SUCCESS = "workspace.tool.success"

# Error message when workspace.tool.success is False
WORKSPACE_TOOL_ERROR = "workspace.tool.error"

# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

WORKFLOW_NAME = "workflow.name"
WORKFLOW_STEP_COUNT = "workflow.step_count"
WORKFLOW_INPUT_SCHEMA = "workflow.input_schema"
WORKFLOW_OUTPUT_SCHEMA = "workflow.output_schema"

# ---------------------------------------------------------------------------
# Workflow step (shared by WorkflowStep, Parallel, Conditional)
# ---------------------------------------------------------------------------

STEP_NAME = "step.name"

# "WorkflowStep" | "ParallelWorkflowStep" | "ConditionalWorkflowStep"
STEP_TYPE = "step.type"

STEP_INPUT_SCHEMA = "step.input_schema"
STEP_OUTPUT_SCHEMA = "step.output_schema"

# Parallel: number of branches run concurrently
STEP_BRANCH_COUNT = "step.branch_count"

# Conditional: the branch key that was selected by the condition function
STEP_BRANCH_SELECTED = "step.branch_selected"

# Comma-separated list of available branch keys
STEP_BRANCH_KEYS = "step.branch_keys"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

APP_NAME = "app.name"
APP_WORKFLOW_ID = "app.workflow_id"

# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

ERROR_TYPE = "error.type"
ERROR_MESSAGE = "error.message"


__all__ = [
    # Span names
    "SPAN_APP_EXECUTE_WORKFLOW",
    "SPAN_AGENT_GENERATE",
    "SPAN_AGENT_GENERATE_STREAM",
    "SPAN_AGENT_GENERATE_STRUCTURED",
    "SPAN_AGENT_GENERATE_WITH_EVALS",
    "SPAN_AGENT_TOOL_CALL",
    "SPAN_LLM_CHAT",
    "SPAN_LLM_CHAT_STREAM",
    "SPAN_WORKFLOW_EXECUTE",
    "SPAN_WORKFLOW_STEP_EXECUTE",
    "SPAN_WORKFLOW_STEP_PARALLEL",
    "SPAN_WORKFLOW_STEP_CONDITIONAL",
    "SPAN_WORKSPACE_TOOL",
    # GenAI
    "GEN_AI_SYSTEM",
    "GEN_AI_OPERATION_NAME",
    "GEN_AI_REQUEST_MODEL",
    "GEN_AI_RESPONSE_MODEL",
    "GEN_AI_USAGE_INPUT_TOKENS",
    "GEN_AI_USAGE_OUTPUT_TOKENS",
    "GEN_AI_USAGE_TOTAL_TOKENS",
    "GEN_AI_USAGE_THINKING_TOKENS",
    "GEN_AI_USAGE_CACHE_READ_TOKENS",
    "GEN_AI_USAGE_CACHE_CREATION_TOKENS",
    "GEN_AI_RESPONSE_FINISH_REASON",
    "GEN_AI_THINKING_ENABLED",
    "GEN_AI_THINKING_BUDGET_TOKENS",
    "GEN_AI_REQUEST_TEMPERATURE",
    "GEN_AI_REQUEST_MAX_TOKENS",
    "GEN_AI_REQUEST_TOP_P",
    # LLM call
    "LLM_MESSAGE_COUNT",
    "LLM_ITERATION",
    "LLM_HAS_TOOLS",
    "LLM_TOOL_DEFINITION_COUNT",
    "LLM_RETURNED_TOOL_CALLS",
    # Agent
    "AGENT_NAME",
    "AGENT_DESCRIPTION",
    "AGENT_PROMPT_LENGTH",
    "AGENT_PROMPT",
    "AGENT_RESPONSE_LENGTH",
    "AGENT_RESPONSE",
    "EVENT_USER_MESSAGE",
    "EVENT_ASSISTANT_MESSAGE",
    "EVENT_TOOL_CALL",
    "EVENT_TOOL_RESULT",
    "AGENT_TOOL_COUNT",
    "AGENT_HAS_TOOLS",
    "AGENT_HAS_SCORERS",
    "AGENT_RESPONSE_MODEL",
    "AGENT_HAS_HISTORY",
    "AGENT_TOTAL_ITERATIONS",
    "AGENT_TOTAL_TOOL_CALLS",
    # Agent tool dispatch
    "TOOL_NAME",
    "TOOL_TYPE",
    "TOOL_INPUT",
    "TOOL_OUTPUT",
    "TOOL_RESULT_LENGTH",
    # Workspace tool
    "WORKSPACE_NAME",
    "WORKSPACE_TOOL_CATEGORY",
    "WORKSPACE_TOOL_SUCCESS",
    "WORKSPACE_TOOL_ERROR",
    # Workflow
    "WORKFLOW_NAME",
    "WORKFLOW_STEP_COUNT",
    "WORKFLOW_INPUT_SCHEMA",
    "WORKFLOW_OUTPUT_SCHEMA",
    # Workflow step
    "STEP_NAME",
    "STEP_TYPE",
    "STEP_INPUT_SCHEMA",
    "STEP_OUTPUT_SCHEMA",
    "STEP_BRANCH_COUNT",
    "STEP_BRANCH_SELECTED",
    "STEP_BRANCH_KEYS",
    # App
    "APP_NAME",
    "APP_WORKFLOW_ID",
    # Error
    "ERROR_TYPE",
    "ERROR_MESSAGE",
]
