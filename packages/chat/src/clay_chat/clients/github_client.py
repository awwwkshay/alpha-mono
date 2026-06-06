from __future__ import annotations

import asyncio
from typing import Any

from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository

from clay_chat.log import logger


class GithubClient:
    """Async-friendly wrapper around PyGithub."""

    def __init__(self, *, token: str) -> None:
        self._gh = Github(login_or_token=token)

    async def get_repo(self, owner: str, name: str) -> Repository:
        logger.debug(f"Fetching repo {owner}/{name}")
        return await asyncio.to_thread(self._gh.get_repo, f"{owner}/{name}")

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> Issue:
        logger.debug(f"Creating issue in {owner}/{repo}: {title}")
        repository = await self.get_repo(owner, repo)
        kwargs: dict[str, Any] = {"title": title, "body": body}
        if labels:
            kwargs["labels"] = labels
        return await asyncio.to_thread(repository.create_issue, **kwargs)

    async def list_prs(
        self,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> list[PullRequest]:
        logger.debug(f"Listing {state} PRs in {owner}/{repo}")
        repository = await self.get_repo(owner, repo)
        paginated = await asyncio.to_thread(repository.get_pulls, state=state)
        return [pr for pr in await asyncio.to_thread(list, paginated)]  # type: ignore[return-value]

    async def close(self) -> None:
        await asyncio.to_thread(self._gh.close)


__all__ = ["GithubClient"]
