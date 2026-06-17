"""AgentRunner — 包装 AgentLoop.run()，映射 LoopEvent 为 VizEvent 并广播到 EventBus。"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.viz_event import (
    ConfigPayload,
    PromptBlockPayload,
    SystemPromptPayload,
    VizEvent,
)


def _infer_tool_source(name: str) -> str:
    """从工具名推断来源：mcp__ 前缀 → mcp；否则 builtin。"""
    if name.startswith("mcp__"):
        return "mcp"
    return "builtin"


def _build_config_payload(loop: AgentLoop) -> dict[str, Any]:
    """从 AgentLoop 提取运行配置（不可变：返回新 dict）。"""
    profile = loop.profile
    return ConfigPayload(
        model=loop.model,
        max_steps=loop.max_steps,
        profile=profile.name if profile is not None else None,
        permission_mode=profile.permission_mode if profile is not None else None,
        tools=[d.name for d in loop.router.registry.get_definitions()],
    ).model_dump()


def _build_system_prompt_payload(loop: AgentLoop) -> dict[str, Any]:
    """从 AgentLoop 提取 system prompt（文本 + 结构化块）。"""
    blocks = [
        PromptBlockPayload(
            name=b.name, content=b.content, source=b.source, stability=b.stability,
        )
        for b in loop.system_prompt_blocks
    ]
    return SystemPromptPayload(
        text=loop.system_prompt_text, blocks=blocks,
    ).model_dump()


class AgentRunner:
    """1:1 包装单个 AgentLoop，将执行状态映射为可视化事件。

    持有 AgentLoop 引用以在 wrap() 启动时提取 config/system_prompt 元数据；
    session_id 用于前端按会话过滤事件。
    """

    def __init__(self, loop: AgentLoop, bus: EventBus, session_id: str) -> None:
        self._loop = loop
        self._bus = bus
        self._session_id = session_id

    async def wrap(
        self, loop_gen: AsyncGenerator[LoopEvent, None],
    ) -> AsyncGenerator[LoopEvent, None]:
        """消费 AgentLoop.run()，发布 VizEvent，透传原始 LoopEvent。

        启动时先发 config + system_prompt + idle（会话级快照），
        随后映射每个 LoopEvent，结束发 shutdown。
        """
        await self._publish("config", _build_config_payload(self._loop))
        await self._publish("system_prompt", _build_system_prompt_payload(self._loop))
        await self._publish("idle", {})

        try:
            async for event in loop_gen:
                for viz in self._map(event):
                    await self._bus.publish(viz.model_dump())
                yield event
        except Exception as exc:
            await self._publish("error", {"error": str(exc)})
            raise
        finally:
            await self._publish("shutdown", {})

    def _map(self, event: LoopEvent) -> list[VizEvent]:
        """将 LoopEvent 映射为零或多个 VizEvent。"""
        event_type = event.type
        data = event.data

        if event_type == "step":
            stop_reason = data.get("stop_reason")
            if stop_reason == "tool_use":
                return [self._make_viz("thinking", {"step": event.step, **data})]
            if stop_reason in ("end_turn", "stop_sequence"):
                return [self._make_viz("done", {"step": event.step, **data})]
            return []

        if event_type == "tool_result":
            results: list[VizEvent] = []
            tool_calls = data.get("tool_calls", [])
            tool_results_raw = data.get("tool_results", [])

            for i, tc in enumerate(tool_calls):
                result_content = tool_results_raw[i] if i < len(tool_results_raw) else ""
                tc_id = tc.get("id", "")
                tc_name = tc.get("name", "")
                tc_input = tc.get("input", {})
                source = _infer_tool_source(tc_name)

                results.append(self._make_viz("tool_call", {
                    "step": event.step,
                    "tool_call_id": tc_id,
                    "tool_name": tc_name,
                    "params": tc_input,
                    "source": source,
                }))
                results.append(self._make_viz("tool_result", {
                    "step": event.step,
                    "tool_call_id": tc_id,
                    "tool_name": tc_name,
                    "content": result_content,
                    "source": source,
                }))

            return results

        if event_type == "done":
            return [self._make_viz("done", {"step": event.step, **data})]

        if event_type in ("error", "max_steps"):
            return [self._make_viz("error", {"step": event.step, **data})]

        return []

    async def _publish(self, viz_type: str, payload: dict[str, Any]) -> None:
        viz = self._make_viz(viz_type, payload)
        await self._bus.publish(viz.model_dump())

    def _make_viz(self, viz_type: str, payload: dict[str, Any]) -> VizEvent:
        return VizEvent(
            type=viz_type,
            agent=self._session_id,
            session_id=self._session_id,
            payload=payload,
            timestamp=time.time(),
        )
