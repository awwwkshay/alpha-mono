from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ddgs import DDGS
from pydantic import BaseModel, Field

from alpha_app import ParallelWorkflowStepConfig, WorkflowConfig, WorkflowStepConfig

if TYPE_CHECKING:
    from alpha_app import AppContext


class DailyBriefInput(BaseModel):
    date: str = Field(..., description="Date to brief on (YYYY-MM-DD)")
    location: str | None = Field(
        default=None, description="City/region for weather, e.g. 'London'"
    )


class BriefNewsOutput(BaseModel):
    news_results: str


class BriefWeatherOutput(BaseModel):
    weather_results: str


class DailyBriefData(BaseModel):
    news_results: str
    weather_results: str


async def _fetch_news(inp: DailyBriefInput, _ctx: AppContext) -> BriefNewsOutput:
    query = f"top news headlines {inp.date}"

    def _search() -> list[dict]:
        with DDGS() as ddgs:
            try:
                return [
                    {"title": r["title"], "body": r["body"]}
                    for r in ddgs.news(query, max_results=8)
                ]
            except Exception:
                pass
            try:
                return list(ddgs.text(query, max_results=8))
            except Exception:
                return []

    try:
        results = await asyncio.wait_for(asyncio.to_thread(_search), timeout=15.0)
    except TimeoutError:
        return BriefNewsOutput(news_results="News search timed out.")

    if not results:
        return BriefNewsOutput(news_results="No news results found.")

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')}" for r in results[:8]
    )
    return BriefNewsOutput(news_results=snippets)


async def _fetch_weather(inp: DailyBriefInput, _ctx: AppContext) -> BriefWeatherOutput:
    location = inp.location or "today"
    query = f"weather forecast {location} {inp.date}"

    def _search() -> list[dict]:
        with DDGS() as ddgs:
            try:
                return list(ddgs.text(query, max_results=4))
            except Exception:
                return []

    try:
        results = await asyncio.wait_for(asyncio.to_thread(_search), timeout=15.0)
    except TimeoutError:
        return BriefWeatherOutput(weather_results="Weather search timed out.")

    if not results:
        return BriefWeatherOutput(weather_results="No weather results found.")

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')}" for r in results[:4]
    )
    return BriefWeatherOutput(weather_results=snippets)


_news_step = WorkflowStepConfig.create(
    name="fetch_news",
    input_schema=DailyBriefInput,
    output_schema=BriefNewsOutput,
    execute=_fetch_news,
)

_weather_step = WorkflowStepConfig.create(
    name="fetch_weather",
    input_schema=DailyBriefInput,
    output_schema=BriefWeatherOutput,
    execute=_fetch_weather,
)

_gather_step = ParallelWorkflowStepConfig.create(
    name="gather",
    input_schema=DailyBriefInput,
    output_schema=DailyBriefData,
    branches={"news": _news_step, "weather": _weather_step},
)

daily_brief_workflow = WorkflowConfig.create(
    name="daily_brief",
    description=(
        "Fetch today's top news headlines and weather forecast in parallel. "
        "Returns raw data for the assistant to format into a morning brief."
    ),
    input_schema=DailyBriefInput,
    output_schema=DailyBriefData,
    steps={"gather": _gather_step},
)

__all__ = ["DailyBriefData", "DailyBriefInput", "daily_brief_workflow"]
