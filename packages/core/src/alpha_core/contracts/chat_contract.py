from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChatContract(Protocol):
    """
    Protocol for chat-platform integrations.

    Implement ``mount(app, agent)`` and add an instance to ``AgentConfig.chat``.
    ``AlphaApp`` calls ``integration.mount(app, agent)`` at startup for each entry.

    The ``app`` parameter is an ``AlphaApp`` instance and ``agent`` is an ``Agent``
    instance (both from ``alpha_app``). They are typed as ``Any`` here to keep
    ``alpha_core`` free of dependencies on ``alpha_app``.

    Example::

        from alpha_chat import SlackChat

        AgentConfig(
            ...
            chat=[SlackChat(), TelegramChat()],
        )
    """

    def mount(self, app: Any, agent: Any) -> None: ...


__all__ = ["ChatContract"]
