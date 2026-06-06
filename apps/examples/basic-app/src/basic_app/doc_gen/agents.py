from __future__ import annotations

from pathlib import Path

from clay_app import (
    AnswerRelevancyScorer,
    CompletenessScorer,
)
from clay_core import (
    AgentConfig,
    LocalFilesystemConfig,
    ScorerConfig,
    WorkspaceConfig,
)

_PROMPTS_DIR = Path(__file__).parents[3] / "prompts"
_EVAL_MODEL = "gemini/gemini-2.0-flash"
_MODEL = "gemini/gemini-2.0-flash"


def create_doc_gen_agents(source_dir: Path) -> dict[str, AgentConfig]:
    return {
        "reader": AgentConfig(
            name="File Reader",
            system_prompt_md_path=_PROMPTS_DIR / "reader.md",
            model=_MODEL,
            workspace=WorkspaceConfig(
                name="source",
                filesystem=LocalFilesystemConfig(base_path=source_dir),
            ),
        ),
        "purpose_analyzer": AgentConfig(
            name="Purpose Analyzer",
            system_prompt_md_path=_PROMPTS_DIR / "purpose_analyzer.md",
            model=_MODEL,
            scorers={
                "relevancy": ScorerConfig(
                    scorer=AnswerRelevancyScorer(model=_EVAL_MODEL),
                ),
            },
        ),
        "api_surface": AgentConfig(
            name="API Surface Extractor",
            system_prompt_md_path=_PROMPTS_DIR / "api_surface.md",
            model=_MODEL,
        ),
        "complexity_scorer": AgentConfig(
            name="Complexity Scorer",
            system_prompt_md_path=_PROMPTS_DIR / "complexity_scorer.md",
            model=_MODEL,
        ),
        "full_doc_writer": AgentConfig(
            name="Full Doc Writer",
            system_prompt_md_path=_PROMPTS_DIR / "full_doc_writer.md",
            model=_MODEL,
            scorers={
                "completeness": ScorerConfig(
                    scorer=CompletenessScorer(model=_EVAL_MODEL),
                ),
            },
        ),
        "concise_doc_writer": AgentConfig(
            name="Concise Doc Writer",
            system_prompt_md_path=_PROMPTS_DIR / "concise_doc_writer.md",
            model=_MODEL,
        ),
    }


__all__ = ["create_doc_gen_agents"]
