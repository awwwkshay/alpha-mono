from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import httpx
from ddgs import DDGS
from pydantic import BaseModel, Field

from alpha_app import ParallelWorkflowStepConfig, WorkflowConfig, WorkflowStepConfig

if TYPE_CHECKING:
    from alpha_app import AppContext


class ResearchInput(BaseModel):
    topic: str = Field(..., description="Topic or question to research")


class SearchResultsOutput(BaseModel):
    snippets: str = Field(..., description="Search result snippets for all results")
    url1: str = Field(default="", description="Top result URL")
    url2: str = Field(default="", description="Second result URL")
    url3: str = Field(default="", description="Third result URL")


class Page1Output(BaseModel):
    page1_content: str
    snippets: str


class Page2Output(BaseModel):
    page2_content: str


class Page3Output(BaseModel):
    page3_content: str


class ResearchData(BaseModel):
    snippets: str
    page1_content: str
    page2_content: str
    page3_content: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:  # noqa: ARG002  # pyright: ignore[reportUnusedParameter]
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


async def _fetch_url(url: str) -> str:
    if not url:
        return ""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                follow_redirects=True,
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Jarvis/1.0)"},
            )
            response.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(response.text)
        return extractor.get_text()[:2500]
    except Exception:
        return ""


async def _search_topic(inp: ResearchInput, _ctx: AppContext) -> SearchResultsOutput:
    def _search() -> list[dict]:
        with DDGS() as ddgs:
            try:
                return list(ddgs.text(inp.topic, max_results=8))
            except Exception:
                return []

    try:
        results = await asyncio.wait_for(asyncio.to_thread(_search), timeout=15.0)
    except TimeoutError:
        return SearchResultsOutput(
            snippets="Search timed out.", url1="", url2="", url3=""
        )

    if not results:
        return SearchResultsOutput(
            snippets="No results found.", url1="", url2="", url3=""
        )

    urls = [r.get("href", "") for r in results if r.get("href")]
    while len(urls) < 3:
        urls.append("")

    snippets = "\n\n".join(
        f"[{i + 1}] {r.get('title', '')}\n{r.get('body', '')}\nURL: {r.get('href', '')}"
        for i, r in enumerate(results[:8])
    )
    return SearchResultsOutput(
        snippets=snippets, url1=urls[0], url2=urls[1], url3=urls[2]
    )


async def _fetch_page1(inp: SearchResultsOutput, _ctx: AppContext) -> Page1Output:
    content = await _fetch_url(inp.url1)
    return Page1Output(page1_content=content, snippets=inp.snippets)


async def _fetch_page2(inp: SearchResultsOutput, _ctx: AppContext) -> Page2Output:
    return Page2Output(page2_content=await _fetch_url(inp.url2))


async def _fetch_page3(inp: SearchResultsOutput, _ctx: AppContext) -> Page3Output:
    return Page3Output(page3_content=await _fetch_url(inp.url3))


_search_step = WorkflowStepConfig.create(
    name="search",
    input_schema=ResearchInput,
    output_schema=SearchResultsOutput,
    execute=_search_topic,
)

_page1_step = WorkflowStepConfig.create(
    name="fetch_page1",
    input_schema=SearchResultsOutput,
    output_schema=Page1Output,
    execute=_fetch_page1,
)

_page2_step = WorkflowStepConfig.create(
    name="fetch_page2",
    input_schema=SearchResultsOutput,
    output_schema=Page2Output,
    execute=_fetch_page2,
)

_page3_step = WorkflowStepConfig.create(
    name="fetch_page3",
    input_schema=SearchResultsOutput,
    output_schema=Page3Output,
    execute=_fetch_page3,
)

_fetch_pages_step = ParallelWorkflowStepConfig.create(
    name="fetch_pages",
    input_schema=SearchResultsOutput,
    output_schema=ResearchData,
    branches={"page1": _page1_step, "page2": _page2_step, "page3": _page3_step},
)

research_summarise_workflow = WorkflowConfig.create(
    name="research_summarise",
    description=(
        "Research a topic thoroughly: search the web, then fetch the top 3 source pages "
        "in parallel. Returns raw content for the assistant to synthesize into a report."
    ),
    input_schema=ResearchInput,
    output_schema=ResearchData,
    steps={"search": _search_step, "fetch_pages": _fetch_pages_step},
)

__all__ = ["ResearchData", "ResearchInput", "research_summarise_workflow"]
