"""AgentRunner — 包装 AgentLoop.run()，映射 LoopEvent 为 VizEvent 并广播到 EventBus。"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.viz_event import VizEvent


class AgentRunner:
    """1:1 包装单个 AgentLoop，将执行状态映射为可视化事件。"""

    def __init__(self, agent_name: str, bus: EventBus) -> None:
        self._agent_name = agent_name
        self._bus = bus

    async def wrap(
        self, loop_gen: AsyncGenerator[LoopEvent, None],
    ) -> AsyncGenerator[LoopEvent, None]:
        """消费 AgentLoop.run()，发布 VizEvent，透传原始 LoopEvent。"""
        await self._publish("idle", {})

        try:
            async for event in loop_gen:
                viz = self._map(event)
                if viz is not None:
                    await self._bus.publish(viz.model_dump())
                yield event
        except Exception as exc:
            await self._publish("error", {"error": str(exc)})
            raise
        finally:
            await self._publish("shutdown", {})

    def _map(self, event: LoopEvent) -> VizEvent | None:
        """将 LoopEvent 映射为 VizEvent（per D-07）。"""
        event_type = event.type
        data = event.data

        if event_type == "step":
            stop_reason = data.get("stop_reason")
            if stop_reason == "tool_use":
                return self._make_viz("thinking", {"step": event.step, **data})
            if stop_reason in ("end_turn", "stop_sequence"):
                return self._make_viz("done", {"step": event.step, **data})
            return None

        if event_type == "tool_result":
            return self._make_viz("tool_call", {"step": event.step, **data})

        if event_type == "done":
            return self._make_viz("done", {"step": event.step, **data})

        if event_type in ("error", "max_steps"):
            return self._make_viz("error", {"step": event.step, **data})

        return None

    async def _publish(self, viz_type: str, payload: dict[str, Any]) -> None:
        viz = self._make_viz(viz_type, payload)
        await self._bus.publish(viz.model_dump())

    def _make_viz(self, viz_type: str, payload: dict[str, Any]) -> VizEvent:
        return VizEvent(
            type=viz_type,
            agent=self._agent_name,
            payload=payload,
            timestamp=time.time(),
        )
