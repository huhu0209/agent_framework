# Phase 23: Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

为剩余 5 个模块添加适配器方法，使它们能通过 ConfigLoader.discover() 自动初始化：
1. **AgentConfig.from_loader()**（ADP-04）— 从 discover("agents") 路径加载 agent 配置，同名碰撞 warning
2. **AgentProfile.from_profile()**（ADP-05）— 从 discover("profiles") 加载指定 profile 目录，global+project 字段级合并
3. **McpManager.from_loader()**（ADP-06）— 从 discover("mcp") 路径合并 servers.json，同名覆盖 + warning
4. **TaskManager 默认路径**（ADP-07）— tasks_dir 默认值改为 .agent-framework/tasks/
5. **PermissionPipeline.from_loader()**（ADP-08）— 从 Settings.permissions 注入 allow/deny 列表

向后兼容（ADP-09）— 所有现有构造函数签名不变（TaskManager 仅添加默认参数），工厂方法/类方法为纯新增 API。所有 1002+ 现有测试必须通过。

</domain>

<decisions>
## Implementation Decisions

### AgentConfig vs AgentProfile 归属
- **D-01:** 拆分职责：`AgentConfig.from_loader(loader)` 负责 discover("agents") 的 .md 配置加载，`AgentProfile.from_profile(loader, name)` 负责 discover("profiles") 的 profile 目录加载。不合并为单一类
- **D-02:** `AgentConfig.from_loader()` 返回 `dict[str, AgentConfig]`，复用现有 `load_agent_configs()` 的合并语义
- **D-03:** `AgentConfig.from_loader()` 作为 `@classmethod`，与 Phase 22 的 from_loader() 范式一致

### Agent 名称碰撞与 warning 策略
- **D-04:** 名称碰撞时使用 `logger.warning()` 发出警告，与现有代码库风格一致（不用 print 或返回报告）
- **D-05:** 加载顺序：反转 discover() 返回的 [global, project] 顺序为 [project, global]，project 后加载自然覆盖 global 的同名 key。碰撞时 logger.warning 提示被覆盖的名称和来源路径
- **D-06:** `AgentProfile.from_profile(loader, name)` 先加载 global 目录的 profile 子文件（soul.md/agents.md/identity.md/tool_guidance.md），再用 project 目录的非空字段覆盖。与 Phase 21 ConfigLoader.load_profile() 语义一致

### MCP servers.json 合并策略
- **D-07:** 同名 MCP server 出现在 global 和 project 的 servers.json 时，project 完全覆盖 global 的 McpServerConfig，logger.warning() 提示碰撞
- **D-08:** 逐目录读取 servers.json，按 discover() 原序（global → project）加载。类似 HookManager 的 load_from_json 模式——先构建 global 的 dict，再逐个用 project 的条目覆盖
- **D-09:** 容错策略：servers.json 文件不存在时跳过该目录（正常情况），JSON 格式错误或单个 server 条目无效时 logger.warning() + 跳过该条目

### TaskManager 默认路径（ADP-07）
- **D-10:** 修改 `TaskManager.__init__(tasks_dir: Path = Path.cwd() / ".agent-framework" / "tasks")`，添加默认参数值。向后兼容——现有调用方已显式传入 tasks_dir，不受影响

### PermissionPipeline 权限注入（ADP-08）
- **D-11:** 添加 `PermissionPipeline.from_loader(loader, profile_name: str)` 工厂方法。内部调用 `AgentProfile.from_profile(loader, profile_name)` 获取 profile，再从 `loader.load_settings().permissions` 获取 PermissionsConfig
- **D-12:** 权限优先级：Settings.permissions 作为全局基准（allow/deny/ask 列表），AgentProfile 的 allowed_tools/disallowed_tools 在此基础上追加。permission_mode 保持从 AgentProfile 读取

### Claude's Discretion
- `AgentConfig.from_loader()` 的具体多目录遍历实现——推荐反转 discover 顺序后逐目录调用 load_agent_configs()，合并 dict 时检测碰撞
- `AgentProfile.from_profile()` 的具体字段合并逻辑——推荐复用 AgentProfile.from_directory() 获取两个 profile，然后非空字段覆盖
- `McpManager.from_loader()` 的 JSON 解析和 McpServerConfig 验证——推荐用 McpServerConfig.model_validate() 逐条解析
- `PermissionPipeline.from_loader()` 中 Settings permissions 和 Profile permissions 的具体合并实现方式
- 测试文件组织和测试用例设计
- 各 from_loader() 方法的 docstring 具体措辞

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 设计文档（核心参考）
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整的路径机制设计：模块发现机制、适配器设计意图、servers.json 结构

### 需求定义
- `.planning/REQUIREMENTS.md` — ADP-04（AgentProfile.from_loader）、ADP-05（AgentProfile.from_profile）、ADP-06（McpManager.from_loader）、ADP-07（TaskManager 默认路径）、ADP-08（PermissionPipeline 注入）、ADP-09（向后兼容）
- `.planning/ROADMAP.md` — Phase 23 目标、成功标准、范围定义

### Phase 21 已实现代码（依赖）
- `framework/agent_framework/config/loader.py` — ConfigLoader 类 + discover() 方法 + load_settings() + load_profile()
- `framework/agent_framework/config/settings.py` — Settings 模型 + PermissionsConfig(allow, deny, ask)

### Phase 22 已实现代码（范式参考）
- `framework/agent_framework/skills/registry.py` — SkillRegistry.from_loader() 范式：@classmethod + loader.discover() + 反转顺序
- `framework/agent_framework/hooks/manager.py` — HookManager.from_loader() 范式：逐目录 load_from_json + 碰撞合并
- `framework/agent_framework/commands/dispatcher.py` — CommandDispatcher.from_loader() 范式：链式 from_loader

### 本 phase 需修改/扩展的代码
- `framework/agent_framework/agents/config.py` — AgentConfig 类：添加 from_loader() @classmethod
- `framework/agent_framework/prompts/profiles.py` — AgentProfile 类：添加 from_profile() @classmethod
- `framework/agent_framework/tools/mcp/config.py` — McpManager 类：添加 from_loader() @classmethod
- `framework/agent_framework/tasks/manager.py` — TaskManager 类：修改 __init__ 默认参数
- `framework/agent_framework/safety/permissions.py` — PermissionPipeline 类：添加 from_loader() @classmethod

### 参考代码（不修改）
- `framework/agent_framework/commands/dispatcher.py` — 链式 from_loader 参考模式（PermissionPipeline 将类似地链式调用 AgentProfile.from_profile）

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Pydantic 模型惯例、不可变模式、docstring 中文描述
- `.planning/codebase/ARCHITECTURE.md` — 框架层次、叶依赖约束

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigLoader.discover(module_name) -> list[Path]` — Phase 21 已实现，返回 [global, project] 优先级目录列表
- `load_agent_configs(directory: Path) -> dict[str, AgentConfig]` — 已有单目录加载逻辑，from_loader() 需多目录调用并合并
- `AgentProfile.from_directory(path: Path) -> AgentProfile` — 已有单目录加载逻辑，from_profile() 需调用两次并合并
- `McpServerConfig.model_validate(dict)` — Pydantic 验证，McpManager.from_loader() 用它解析 JSON 条目
- `HookManager.from_loader()` — 逐目录 load_from_json + 合并的完整范式，McpManager 直接参考

### Established Patterns
- @classmethod from_loader() — Phase 22 建立的标准范式
- Additive API — v0.0.6 核心约束：不修改现有构造函数签名（TaskManager 仅加默认值）
- 叶依赖约束 — config/ 不导入框架其他模块，但适配器（agents/prompts/tools/tasks/safety）可以导入 config/
- logger.warning() 碰撞提示 — 统一的 warning 模式
- 反转 discover 顺序 — project 覆盖 global 的统一策略

### Integration Points
- Phase 24 的 backend 集成将通过 ConfigLoader + from_loader() 一键初始化所有模块
- Phase 24 的 PromptAssembler 将集成 AgentProfile.from_profile() 获取的 profile
- PermissionPipeline.from_loader() 是 Phase 24 ToolRouter 完整初始化的关键环节

### Concerns
- **PermissionPipeline 权限合并语义** — Settings.permissions（工具名 glob 模式列表）和 AgentProfile（allowed_tools/disallowed_tools）是两种不同粒度的权限定义。合并时需注意去重和冲突处理
- **McpServerConfig 验证** — 现有 _reject_sensitive_env_keys validator 在 from_loader() 解析时仍需生效

</code_context>

<specifics>
## Specific Ideas

- AgentConfig.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader) -> dict[str, AgentConfig]:
      paths = loader.discover("agents")
      # 反转：project 优先
      reversed_paths = list(reversed(paths))
      result: dict[str, AgentConfig] = {}
      for path in reversed_paths:
          configs = load_agent_configs(path)
          for name, config in configs.items():
              if name in result:
                  logger.warning("Agent '%s' from %s overrides global", name, path)
              result[name] = config
      return result
  ```

- AgentProfile.from_profile() 实现思路：
  ```python
  @classmethod
  def from_profile(cls, loader: ConfigLoader, name: str) -> AgentProfile:
      profile_files = loader.load_profile(name)
      # load_profile() 已实现 global + project 字段级合并
      # 用合并后的 dict 构造 AgentProfile
      return cls(name=name, **{k: v for k, v in profile_files.items() if v})
  ```

- McpManager.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader) -> McpManager:
      server_map: dict[str, McpServerConfig] = {}
      for mcp_dir in loader.discover("mcp"):
          servers_file = mcp_dir / "servers.json"
          if not servers_file.exists():
              continue
          # 解析 JSON，逐条 model_validate，同名覆盖 + warning
          ...
      return cls(configs=list(server_map.values()))
  ```

- PermissionPipeline.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader, profile_name: str) -> PermissionPipeline:
      profile = AgentProfile.from_profile(loader, profile_name)
      settings = loader.load_settings()
      # 合并 permissions: settings 为基准，profile 追加
      ...
      return cls(profile=profile)
  ```

- TaskManager 默认参数：
  ```python
  def __init__(self, tasks_dir: Path = Path.cwd() / ".agent-framework" / "tasks") -> None:
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions*
*Context gathered: 2026-06-11*
