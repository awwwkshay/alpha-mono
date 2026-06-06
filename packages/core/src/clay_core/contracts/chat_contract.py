from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChatContract(Protocol):
    """
    Protocol for chat-platform integrations.

    Implement ``mount(app, agent)`` and add an instance to ``AgentConfig.chat``.
    ``ClayApp`` calls ``integration.mount(app, agent)`` at startup for each entry.

    The ``app`` parameter is a ``ClayApp`` instance, ``agent`` is an ``Agent``
    instance, and ``agent_id`` is the key the agent was registered under in
    ``AppConfig.agents``. All three are typed as ``Any`` / ``str`` here to keep
    ``clay_core`` free of dependencies on ``clay_app``.

    The ``agent_id`` is used by platform integrations to build per-agent URL
    prefixes (e.g. ``/slack/<agent_id>/events``).

    Example::

        from clay_chat import SlackChat

        AgentConfig(
            ...
            chat=[SlackChat(), TelegramChat()],
        )
    """

    def mount(self, app: Any, agent: Any, agent_id: str) -> None: ...

    async def setup(self) -> None:
        """Called by ClayApp.setup() after all routers are mounted. Override to run async init (e.g. webhook registration)."""


__all__ = ["ChatContract"]
