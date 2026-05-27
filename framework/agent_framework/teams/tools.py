"""Team 工具 — 供 Agent 调用的 spawn/send/read/broadcast。"""

from __future__ import annotations

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.teams.bus import MessageBus
from agent_framework.teams.manager import TeamManager
from agent_framework.teams.types import TeammateConfig
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext


def create_team_tools(
    team_manager: TeamManager,
    bus: MessageBus,
) -> list[ToolSpec]:
    """创建 5 个 team 工具，返回 ToolSpec 列表。"""

    async def _spawn_teammate(
        args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        config = TeammateConfig(
            name=args["name"],
            role=args.get("role", "worker"),
            system_prompt=args.get("system_prompt", ""),
            allowed_tools=args.get("allowed_tools"),
        )
        await team_manager.spawn(config)
        return ToolResult(content=f"已创建队友 {config.name}")

    async def _list_teammates(
        args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        board = team_manager.list_all()
        return ToolResult(content=board)

    async def _send_message(
        args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        sender = ctx.extra.get("teammate_name", "lead")
        to = args["to"]
        content = args["content"]
        bus.send(sender, to, content)
        return ToolResult(content=f"已发送消息给 {to}")

    async def _read_inbox(
        args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        name = ctx.extra.get("teammate_name", "lead")
        messages = bus.read_inbox(name)
        if not messages:
            return ToolResult(content="(收件箱为空)")
        lines = [f"[{m.from_}] {m.content}" for m in messages]
        return ToolResult(content="\n".join(lines))

    async def _broadcast(
        args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        sender = ctx.extra.get("teammate_name", "lead")
        content = args["content"]
        teammates = list(team_manager._configs.keys())
        bus.broadcast(sender, teammates, content)
        return ToolResult(content=f"已广播给 {len(teammates)} 个队友")

    return [
        ToolSpec(
            name="spawn_teammate",
            description="创建一个新的队友 agent",
            parameters=ToolParameterSchema(
                properties={
                    "name": {"type": "string", "description": "队友名称"},
                    "role": {"type": "string", "description": "队友角色"},
                    "system_prompt": {"type": "string", "description": "系统提示词"},
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "允许使用的工具列表",
                    },
                },
                required=["name"],
            ),
            handler=_spawn_teammate,
        ),
        ToolSpec(
            name="list_teammates",
            description="列出所有队友及其状态",
            parameters=ToolParameterSchema(),
            handler=_list_teammates,
        ),
        ToolSpec(
            name="send_message",
            description="向指定队友发送消息",
            parameters=ToolParameterSchema(
                properties={
                    "to": {"type": "string", "description": "接收者名称"},
                    "content": {"type": "string", "description": "消息内容"},
                },
                required=["to", "content"],
            ),
            handler=_send_message,
        ),
        ToolSpec(
            name="read_inbox",
            description="读取自己的收件箱",
            parameters=ToolParameterSchema(),
            handler=_read_inbox,
        ),
        ToolSpec(
            name="broadcast",
            description="向所有队友广播消息",
            parameters=ToolParameterSchema(
                properties={
                    "content": {"type": "string", "description": "广播内容"},
                },
                required=["content"],
            ),
            handler=_broadcast,
        ),
    ]
