from __future__ import annotations

import asyncio
import logging
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import httpx
from ddgs import DDGS
from pydantic import BaseModel, Field

from alpha_core.domain.agent.tool.agent_tool import AgentTool

if TYPE_CHECKING:
    from alpha_core.schemas.app_context import AppContext

logger = logging.getLogger("personal_agent")


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query")


class WebSearchOutput(BaseModel):
    results: str


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


_SEARCH_TIMEOUT = 15.0  # seconds per DDGS search attempt


async def _execute(inp: WebSearchInput, _ctx: AppContext) -> WebSearchOutput:
    logger.info(f"web_search: query={inp.query!r}")

    def _search() -> list[dict]:
        with DDGS() as ddgs:
            try:
                news = [
                    {"title": r["title"], "body": r["body"], "href": r["url"]}
                    for r in ddgs.news(inp.query, max_results=5)
                ]
            except Exception as exc:
                logger.debug(f"web_search: news search failed: {exc}")
                news = []
            try:
                text = list(ddgs.text(inp.query, max_results=5))
            except Exception as exc:
                logger.debug(f"web_search: text search failed: {exc}")
                text = []

        seen: set[str] = set()
        combined: list[dict] = []
        for r in news + text:
            url = r.get("href", "")
            if url and url not in seen:
                seen.add(url)
                combined.append(r)
        return combined

    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(_search), timeout=_SEARCH_TIMEOUT
        )
    except TimeoutError:
        logger.warning(
            f"web_search: timed out after {_SEARCH_TIMEOUT}s for query={inp.query!r}"
        )
        return WebSearchOutput(
            results="Search timed out. Please try a simpler or more specific query."
        )

    if not results:
        logger.info("web_search: no results found")
        return WebSearchOutput(
            results="No results found. Try a different search query."
        )

    logger.info(f"web_search: got {len(results)} results")
    snippets = "\n\n".join(
        f"[{i + 1}] {r['title']}\n{r['body']}\nURL: {r['href']}"
        for i, r in enumerate(results[:8])
    )
    top_url = results[0]["href"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                top_url,
                follow_redirects=True,
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Jarvis/1.0)"},
            )
            response.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(response.text)
        page_content = extractor.get_text()[:3000]
        combined = f"Top result ({top_url}):\n{page_content}\n\n---\nOther results:\n{snippets}"
    except Exception as exc:
        logger.debug(f"web_search: page fetch failed for {top_url}: {exc}")
        combined = snippets

    return WebSearchOutput(results=combined)


web_search_tool: AgentTool[WebSearchInput, WebSearchOutput] = AgentTool(
    name="web_search",
    description=(
        "Search the web for up-to-date information. Returns the full content of the top "
        "result plus snippets from other results."
    ),
    input_schema=WebSearchInput,
    output_schema=WebSearchOutput,
    execute=_execute,
)

__all__ = ["web_search_tool"]
