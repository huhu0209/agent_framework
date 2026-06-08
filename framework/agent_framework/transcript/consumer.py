"""TranscriptConsumer — 透明包装 LoopEvent generator，录制 transcript。"""

import time
from collections.abc import AsyncGenerator
from typing import Any

from agent_framework.transcript.types import TranscriptEvent, TranscriptEventType
from agent_framework.transcript.writer import TranscriptWriter


class TranscriptConsumer:
    def __init__(self, writer: TranscriptWriter, *, system_prompt: str | None = None) -> None:
        self._writer = writer
        self._system_prompt = system_prompt

    async def wrap(
        self,
        gen: AsyncGenerator[Any, None],
        user_message: str,
    ) -> AsyncGenerator[Any, None]:
        if self._system_prompt is not None:
            self._writer.write(TranscriptEvent(
                type=TranscriptEventType.SYSTEM,
                timestamp=time.time(),
                content=self._system_prompt,
            ))

        self._writer.write(TranscriptEvent(
            type=TranscriptEventType.USER,
            timestamp=time.time(),
            content=user_message,
        ))

        async for event in gen:
            if event.type == "step":
                self._writer.write(TranscriptEvent(
                    type=TranscriptEventType.ASSISTANT,
                    timestamp=time.time(),
                    content=event.data.get("content", []),
                ))
            elif event.type == "tool_result":
                tool_calls = event.data.get("tool_calls", [])
                tool_results = event.data.get("tool_results", [])
                for tc, tr in zip(tool_calls, tool_results):
                    self._writer.write(TranscriptEvent(
                        type=TranscriptEventType.TOOL_RESULT,
                        timestamp=time.time(),
                        content=tr,
                        tool_call_id=tc["id"],
                        tool_name=tc["name"],
                    ))
            yield event
