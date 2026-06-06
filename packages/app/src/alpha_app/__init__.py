# Backwards-compatible core re-exports. New application code should import
# config, contracts, context, and tool abstractions directly from alpha_core.
from alpha_core import (
    AgentConfig,
    AgentTool,
    AppConfig,
    AppContext,
    ConditionalWorkflowStepConfig,
    E2BSandboxConfig,
    FileSystemContract,
    FilesystemConfig,
    LocalFilesystemConfig,
    LocalSandboxConfig,
    ObservabilityConfig,
    ParallelWorkflowStepConfig,
    S3FilesystemConfig,
    SamplingConfig,
    SandboxConfig,
    SandboxContract,
    Scorer,
    ScorerConfig,
    ScorerResult,
    ServerConfig,
    SkillsConfig,
    WorkflowConfig,
    WorkflowStepConfig,
    WorkspaceConfig,
    logger,
)
from alpha_app.agent import Agent
from alpha_app.app import AlphaApp
from alpha_app.evals import (
    AnswerRelevancyScorer,
    BiasScorer,
    CompletenessScorer,
    EvalCase,
    EvalResult,
    FaithfulnessScorer,
    HallucinationScorer,
    KeywordCoverageScorer,
    ToxicityScorer,
    run_evals,
    run_scorers,
)
from alpha_app.workflow import Workflow
from alpha_app.workspace import (
    E2BSandbox,
    LocalFileSystem,
    LocalSandbox,
    S3FileSystem,
    Skill,
    Workspace,
)

_CHAT_EXPORTS = {
    "ChatContract",
    "GithubClient",
    "SlackChat",
    "SlackClient",
    "TelegramChat",
    "TelegramClient",
    "build_slack_router",
    "build_telegram_router",
}


def __getattr__(name: str):
    # Skip dunder/private names and anything not in our declared exports fast,
    # to avoid an alpha_chat import attempt on every missing-attribute lookup.
    if name.startswith("_") or name not in _CHAT_EXPORTS:
        raise AttributeError(f"module 'alpha_app' has no attribute {name!r}")
    try:
        import alpha_chat
    except ImportError as exc:
        raise ImportError(
            "Chat integrations are optional. Install alpha-chat to access "
            f"alpha_app.{name}."
        ) from exc
    # Use alpha_chat as the authoritative source — don't re-check _CHAT_EXPORTS here so
    # that new symbols added to alpha_chat are automatically forwarded once _CHAT_EXPORTS
    # is updated to include them.
    try:
        return getattr(alpha_chat, name)
    except AttributeError:
        raise AttributeError(
            f"alpha_chat does not export {name!r}"
        ) from None


__all__ = [
    # Backwards-compatible alpha_chat re-exports. Prefer importing these from
    # alpha_chat in new application code.
    "ChatContract",
    "GithubClient",
    "SlackChat",
    "SlackClient",
    "TelegramChat",
    "TelegramClient",
    "build_slack_router",
    "build_telegram_router",
    # alpha_core contracts
    "AgentTool",
    "FileSystemContract",
    "SamplingConfig",
    "SandboxContract",
    "Scorer",
    "ScorerConfig",
    "ScorerResult",
    # alpha_core schemas
    "AgentConfig",
    "AppConfig",
    "AppContext",
    "ConditionalWorkflowStepConfig",
    "E2BSandboxConfig",
    "FilesystemConfig",
    "LocalFilesystemConfig",
    "LocalSandboxConfig",
    "ObservabilityConfig",
    "ParallelWorkflowStepConfig",
    "S3FilesystemConfig",
    "SandboxConfig",
    "ServerConfig",
    "SkillsConfig",
    "WorkflowConfig",
    "WorkflowStepConfig",
    "WorkspaceConfig",
    # alpha_core utils
    "logger",
    # alpha_app domain
    "Agent",
    "AlphaApp",
    "AnswerRelevancyScorer",
    "BiasScorer",
    "CompletenessScorer",
    "E2BSandbox",
    "EvalCase",
    "EvalResult",
    "FaithfulnessScorer",
    "HallucinationScorer",
    "KeywordCoverageScorer",
    "LocalFileSystem",
    "LocalSandbox",
    "S3FileSystem",
    "Skill",
    "ToxicityScorer",
    "Workflow",
    "Workspace",
    "run_evals",
    "run_scorers",
]
