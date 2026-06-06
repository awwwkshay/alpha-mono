# Backwards-compatible core re-exports. New application code should import
# config, contracts, context, and tool abstractions directly from clay_core.
from clay_core import (
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
from clay_app.agent import Agent
from clay_app.app import ClayApp
from clay_app.evals import (
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
from clay_app.workflow import Workflow
from clay_app.workspace import (
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
    # to avoid a clay_chat import attempt on every missing-attribute lookup.
    if name.startswith("_") or name not in _CHAT_EXPORTS:
        raise AttributeError(f"module 'clay_app' has no attribute {name!r}")
    try:
        import clay_chat
    except ImportError as exc:
        raise ImportError(
            "Chat integrations are optional. Install clay-chat to access "
            f"clay_app.{name}."
        ) from exc
    # Use clay_chat as the authoritative source — don't re-check _CHAT_EXPORTS here so
    # that new symbols added to clay_chat are automatically forwarded once _CHAT_EXPORTS
    # is updated to include them.
    try:
        return getattr(clay_chat, name)
    except AttributeError:
        raise AttributeError(f"clay_chat does not export {name!r}") from None


__all__ = [
    # Backwards-compatible clay_chat re-exports. Prefer importing these from
    # clay_chat in new application code.
    "ChatContract",
    "GithubClient",
    "SlackChat",
    "SlackClient",
    "TelegramChat",
    "TelegramClient",
    "build_slack_router",
    "build_telegram_router",
    # clay_core contracts
    "AgentTool",
    "FileSystemContract",
    "SamplingConfig",
    "SandboxContract",
    "Scorer",
    "ScorerConfig",
    "ScorerResult",
    # clay_core schemas
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
    # clay_core utils
    "logger",
    # clay_app domain
    "Agent",
    "ClayApp",
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
