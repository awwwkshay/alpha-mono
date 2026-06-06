from __future__ import annotations

from unittest.mock import MagicMock, patch

from clay_chat.clients.github_client import GithubClient


async def test_get_repo_calls_github_get_repo():
    mock_repo = MagicMock()
    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo

    with patch("clay_chat.clients.github_client.Github", return_value=mock_gh):
        client = GithubClient(token="ghp_test")
        result = await client.get_repo("owner", "repo")

    mock_gh.get_repo.assert_called_once_with("owner/repo")
    assert result is mock_repo


async def test_create_issue_calls_repository_create_issue():
    mock_issue = MagicMock()
    mock_repo = MagicMock()
    mock_repo.create_issue.return_value = mock_issue
    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo

    with patch("clay_chat.clients.github_client.Github", return_value=mock_gh):
        client = GithubClient(token="ghp_test")
        result = await client.create_issue(
            "owner", "repo", "Bug: something broke", "Details here"
        )

    mock_repo.create_issue.assert_called_once_with(
        title="Bug: something broke", body="Details here"
    )
    assert result is mock_issue


async def test_create_issue_passes_labels():
    mock_repo = MagicMock()
    mock_repo.create_issue.return_value = MagicMock()
    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo

    with patch("clay_chat.clients.github_client.Github", return_value=mock_gh):
        client = GithubClient(token="ghp_test")
        await client.create_issue("owner", "repo", "Title", labels=["bug", "urgent"])

    call_kwargs = mock_repo.create_issue.call_args.kwargs
    assert call_kwargs["labels"] == ["bug", "urgent"]
