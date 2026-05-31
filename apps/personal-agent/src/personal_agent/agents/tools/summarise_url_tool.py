from __future__ import annotations

from html.parser import HTMLParser
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, Field

from alpha_core.domain.agent.tool.agent_tool import AgentTool

if TYPE_CHECKING:
    from alpha_core.schemas.app_context import AppContext


class SummariseUrlInput(BaseModel):
    url: str = Field(..., description="The URL to fetch and read")


class SummariseUrlOutput(BaseModel):
    content: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:  # noqa: ARG002
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


async def _execute(inp: SummariseUrlInput, _ctx: AppContext) -> SummariseUrlOutput:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                inp.url,
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Jarvis/1.0)"},
            )
            response.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(response.text)
        return SummariseUrlOutput(content=extractor.get_text()[:4000])
    except Exception as exc:
        return SummariseUrlOutput(content=f"Could not fetch URL: {exc}")


summarise_url_tool: AgentTool[SummariseUrlInput, SummariseUrlOutput] = AgentTool(
    name="summarise_url",
    description="Fetch and read the full content of a URL.",
    input_schema=SummariseUrlInput,
    output_schema=SummariseUrlOutput,
    execute=_execute,
)

__all__ = ["summarise_url_tool"]
