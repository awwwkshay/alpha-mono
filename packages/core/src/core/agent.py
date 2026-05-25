from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, cast

from core.schemas.agent_config import AgentConfig
from core.schemas.app_context import AppContext

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse


class Agent:
    config: AgentConfig

    def __init__(self, *, config: AgentConfig):
        self.config = config

    async def generate_async(self, user_prompt: str, context: AppContext) -> str:
        from litellm import acompletion

        response = cast(
            "ModelResponse",
            await acompletion(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            ),
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Model returned no content")
        return content

    async def stream_async(
        self, user_prompt: str, context: AppContext
    ) -> AsyncIterator[str]:
        from litellm import acompletion

        response = cast(
            "CustomStreamWrapper",
            await acompletion(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            ),
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta is not None:
                yield delta


__all__ = ["Agent"]
