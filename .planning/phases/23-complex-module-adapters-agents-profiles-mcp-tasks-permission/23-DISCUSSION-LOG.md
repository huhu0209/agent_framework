# Phase 23: Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 23-Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions
**Areas discussed:** AgentConfig vs AgentProfile 归属, Agent 名称碰撞与 warning 策略, MCP servers.json 合并策略, TaskManager 和 PermissionPipeline 集成方式

---

## AgentConfig vs AgentProfile 归属

### Q1: ADP-04 说 "AgentProfile.from_loader()" 但 discover("agents") 是 AgentConfig 的 .md 文件。怎么处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 拆分：AgentConfig + AgentProfile 各管各的 | AgentConfig.from_loader() 加载 discover("agents"), AgentProfile.from_profile() 加载 discover("profiles") | ✓ |
| 合并为单一类 | 将 AgentConfig 和 AgentProfile 合并，改动范围大 | |
| 严格遵循 ADP-04 原文 | 只给 AgentProfile 加 from_loader()，也处理 discover("agents") | |

**User's choice:** 拆分：AgentConfig + AgentProfile 各管各的
**Notes:** 代码库语义完全对齐：agents/ 目录对应 AgentConfig，profiles/ 目录对应 AgentProfile

### Q2: AgentConfig.from_loader() 返回什么类型？

| Option | Description | Selected |
|--------|-------------|----------|
| dict[str, AgentConfig] | 复用现有 load_agent_configs() 语义 | ✓ |
| list[AgentConfig] | 列表风格 | |
| 两者都提供 | 灵活但 API 更复杂 | |

**User's choice:** dict[str, AgentConfig] — 复用现有 load_agent_configs() 语义

### Q3: from_loader() 是 @classmethod 还是 standalone 函数？

| Option | Description | Selected |
|--------|-------------|----------|
| @classmethod | 与 Phase 22 范式一致 | ✓ |
| standalone 函数 | 保持 dataclass 纯净 | |

**User's choice:** @classmethod — 与 Phase 22 范式一致

---

## Agent 名称碰撞与 warning 策略

### Q4: 碰撞 warning 怎么发出？

| Option | Description | Selected |
|--------|-------------|----------|
| logger.warning | 与现有代码风格一致 | ✓ |
| 返回碰撞报告给调用方 | 调用方决定处理方式 | |
| print 到 stderr | 简单但无法过滤 | |

**User's choice:** logger.warning() — 与现有代码风格一致

### Q5: 多目录遍历顺序？

| Option | Description | Selected |
|--------|-------------|----------|
| 反转 discover 顺序，project 后覆盖 | 与 Phase 22 SkillRegistry 策略一致 | ✓ |
| 正向遍历 + 显式碰撞检测 | 逻辑更明确但代码更多 | |

**User's choice:** 反转 discover 顺序，project 后覆盖 global。碰撞时 logger.warning()

### Q6: AgentProfile.from_profile() 合并策略？

| Option | Description | Selected |
|--------|-------------|----------|
| Global+Project 合并，字段级覆盖 | 先加载 global，再用 project 的非空字段覆盖 | ✓ |
| Project 存在则完全覆盖 global | 简单但丢失"全局为基础"语义 | |
| 仅加载 global | 不符合多层级设计 | |

**User's choice:** Global+Project 合并，字段级覆盖。与 Phase 21 loader.load_profile() 语义一致

---

## MCP servers.json 合并策略

### Q7: 同名 MCP server 合并策略？

| Option | Description | Selected |
|--------|-------------|----------|
| Project 覆盖 global（名称碰撞 warning） | 与其他模块策略一致 | ✓ |
| 字段级合并（env/args 追加） | 复杂且可能意外行为 | |
| 全部保留，后缀区分 | 避免碰撞但名称变丑 | |

**User's choice:** Project 覆盖 global，名称碰撞 logger.warning()

### Q8: 加载流程？

| Option | Description | Selected |
|--------|-------------|----------|
| 逐目录读取 servers.json 并合并 | 类似 HookManager 的 load_from_json 模式 | ✓ |
| 合并 JSON 后一次性解析 | 丢失碰撞来源信息 | |

**User's choice:** 逐目录读取 servers.json，按 discover 原序合并

### Q9: 容错策略？

| Option | Description | Selected |
|--------|-------------|----------|
| 文件缺失跳过 + 格式错误 warning | 与 Phase 22 容错策略一致 | ✓ |
| 严格模式：失败则抛异常 | 可能中断启动 | |

**User's choice:** 文件缺失跳过 + 格式错误 logger.warning() 跳过

---

## TaskManager 和 PermissionPipeline 集成方式

### Q10: TaskManager tasks_dir 默认值怎么实现？

| Option | Description | Selected |
|--------|-------------|----------|
| 改 __init__ 默认参数 | 简单直接，向后兼容 | ✓ |
| 添加 from_loader() 方法 | 过度封装 | |
| 不改框架层，Phase 24 处理 | 不满足 ADP-07 | |

**User's choice:** 改 __init__ 默认参数 `Path.cwd() / ".agent-framework" / "tasks"`

### Q11: PermissionPipeline 如何集成 Settings.permissions？

| Option | Description | Selected |
|--------|-------------|----------|
| from_loader() 工厂方法 | 加载 profile + 注入 permissions | ✓ |
| 不改，调用方通过现有 API 注入 | 需调用方自己处理合并 | |
| 修改 __init__ 签名添加 permissions 参数 | 修改现有签名，可能影响 ADP-09 | |

**User's choice:** from_loader() 工厂方法 — 加载 profile + 注入 permissions

### Q12: Settings.permissions 和 AgentProfile 权限的优先级？

| Option | Description | Selected |
|--------|-------------|----------|
| Settings 为基准 + Profile 追加 | 全局基准，项目增强 | ✓ |
| Profile 优先 + Settings 补充 | 语义反转 | |
| Settings 完全替换 Profile 权限 | 丢失 Profile 级别控制 | |

**User's choice:** Settings 为基准 + Profile 追加。permission_mode 保持从 Profile 读取

---

## Claude's Discretion

- AgentConfig.from_loader() 的具体多目录遍历实现细节
- AgentProfile.from_profile() 的字段合并逻辑
- McpManager.from_loader() 的 JSON 解析和验证实现
- PermissionPipeline.from_loader() 中权限合并的具体实现方式
- 测试文件组织和测试用例设计
- 各 from_loader() 方法的 docstring 措辞

## Deferred Ideas

None — discussion stayed within phase scope
