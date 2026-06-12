# Phase 24: Backend Integration + E2E Wiring + Path-Scoped Rules - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

v0.0.6 的最终集成阶段 — 将 Phase 20-23 构建的所有 ConfigLoader + from_loader() 组件连成端到端链路：

1. **Backend Config 集成**（INT-01, INT-02）— backend/app/config 从 ConfigLoader 获取默认值，AgentFactory 通过 ConfigLoader 一键初始化所有模块注册表
2. **Path-Scoped Rules**（INS-03, INT-06）— 新建 rules/ 模块，支持 frontmatter paths 条件匹配加载（Glob 模式）
3. **PromptAssembler 集成**（INS-06）— 修改 assemble() 签名集成指令链 + rules，按设计文档顺序构建完整 system prompt
4. **E2E 验证**（INT-03, INT-04, INT-05）— 叶依赖测试验证、端到端集成测试、1121+ 现有测试零回归

向后兼容约束（已放宽）：PromptAssembler API 不需要保留旧签名（项目未发布）。

</domain>

<decisions>
## Implementation Decisions

### Backend Config 统一（INT-01, INT-02）
- **D-01:** ConfigLoader 作为 fallback — backend Settings (pydantic-settings BaseSettings) 保留 APP_ env vars + .env 文件机制，ConfigLoader.load_settings() 提供默认值，env var 仍为最高优先级
- **D-02:** 并行初始化 — main.py lifespan 中 ConfigLoader 和 backend Settings 独立创建，AgentFactory 同时持有两者
- **D-03:** redis_url 留 backend Settings 独有 — framework Settings 不感知 Redis，保持分离。Backend 独有字段不提升到框架层
- **D-04:** 叶依赖通过测试验证 — 写测试确保 config/ 模块不导入框架其他模块（INT-03）

### Rules 匹配语法（INS-03, INT-06）
- **D-05:** Glob 模式（fnmatch）— paths 使用 Python fnmatch 库，支持 `*` 和 `**` 通配符
- **D-06:** paths 相对于项目根目录（ConfigLoader.project_dir）解析 — 与 discover() 路径一致，行为稳定
- **D-07:** 无 paths frontmatter 的 rules 始终加载 — 用于全局规则（编码风格、安全规范等）
- **D-08:** 新建 `framework/agent_framework/rules/` 模块 — 与 skills/, hooks/ 等模块平级

### PromptAssembler 集成（INS-06）
- **D-09:** 直接修改 `assemble(profile)` 签名为 `assemble(loader, profile, context_path=None)`。不需要 API 向后兼容（项目未发布）
- **D-10:** 严格按设计文档顺序构建 system prompt 块：`<user-provided>` → `<rules>` → `<soul>` → `<instructions>` → `<identity>` → `<skills>` → `<tool-guidance>`
- **D-11:** assemble() 内部调用 `loader.load_agents_md()` 获取指令链注入 `<user-provided>` 块，调用 RuleLoader 加载 rules 注入 `<rules>` 块
- **D-12:** `context_path` 参数过滤 rules — 传当前文件/目录路径给 RuleLoader，只加载 paths 匹配的 rules；无 context_path 时加载所有 rules（含始终加载的）

### AgentFactory 重构深度（INT-02, INT-04）
- **D-13:** 扩展现有 AgentFactory — 新增 `from_configloader(loader, backend_settings)` 工厂方法，保留现有 `from_settings()` 不变
- **D-14:** 单次调用全初始化 — from_configloader() 内部调用所有模块的 from_loader()（SkillRegistry、HookManager、CommandDispatcher、AgentConfig、McpManager、PermissionPipeline），创建带 Profile + Rules + 完整 system prompt 的 AgentLoop
- **D-15:** E2E 验证通过集成测试 — 写独立集成测试验证 ConfigLoader 加载 settings → discover 模块 → 适配器创建注册表 → AgentFactory 创建 AgentLoop 全链路

### Claude's Discretion
- `from_configloader()` 内部各 from_loader() 的具体调用顺序和错误处理策略
- RuleLoader 类的具体 API 设计（类方法 vs 实例方法，是否接受 loader 参数）
- rules/*.md 文件解析的具体 frontmatter 格式（是否复用现有 parse_frontmatter()）
- 集成测试文件组织和测试用例设计
- 叶依赖测试的具体实现方式（AST 分析 vs import 尝试）
- PromptAssembler 新增块的 PromptBlock name/stability/cache_breakpoint 属性值

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 设计文档（核心参考）
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整路径机制设计：目录结构、配置优先级、指令加载链顺序、system prompt 结构、模块发现机制

### 需求定义
- `.planning/REQUIREMENTS.md` — INS-03（rules 条件匹配）、INS-06（PromptAssembler 集成）、INT-01~INT-06（集成与验证）
- `.planning/ROADMAP.md` — Phase 24 目标、成功标准、3 个 plan 拆分建议

### Phase 20-21 已实现代码（依赖）
- `framework/agent_framework/config/loader.py` — ConfigLoader 类 + discover() + load_settings() + load_agents_md() + load_profile()
- `framework/agent_framework/config/settings.py` — Settings 模型 + LlmConfig + PermissionsConfig
- `framework/agent_framework/config/__init__.py` — barrel 导出

### Phase 22-23 已实现代码（适配器）
- `framework/agent_framework/skills/registry.py` — SkillRegistry.from_loader()
- `framework/agent_framework/hooks/manager.py` — HookManager.from_loader()
- `framework/agent_framework/commands/dispatcher.py` — CommandDispatcher.from_loader()
- `framework/agent_framework/agents/config.py` — AgentConfig.from_loader()
- `framework/agent_framework/prompts/profiles.py` — AgentProfile.from_profile()
- `framework/agent_framework/tools/mcp/config.py` — McpManager.from_loader()
- `framework/agent_framework/safety/permissions.py` — PermissionPipeline.from_loader()

### 本 phase 需修改/扩展的代码
- `backend/app/main.py` — lifespan 中并行初始化 ConfigLoader + backend Settings，传给 AgentFactory
- `backend/app/config/__init__.py` — 可能添加从 ConfigLoader 读取默认值的逻辑
- `backend/app/services/agent_factory.py` — 新增 from_configloader() 工厂方法
- `framework/agent_framework/prompts/assembler.py` — 修改 assemble() 签名，集成指令链 + rules

### 本 phase 需新建的代码
- `framework/agent_framework/rules/` — 新模块目录
- `framework/agent_framework/rules/loader.py` — RuleLoader 类（frontmatter paths 解析 + Glob 匹配）
- `framework/agent_framework/rules/__init__.py` — barrel 导出

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Pydantic 模型惯例、不可变模式、docstring 中文描述
- `.planning/codebase/ARCHITECTURE.md` — 框架层次、叶依赖约束

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigLoader.discover("rules")` — Phase 21 MODULE_DIRS 已声明 `"rules": "rules"`，返回 [global, project] 路径列表
- `parse_frontmatter()` — 已有 YAML frontmatter 解析函数，rules 可复用解析 paths 字段
- `SkillRegistry.from_loader(loader)` 等 — Phase 22-23 建立的完整 from_loader() 范式，AgentFactory 可逐个调用
- `PromptAssembler` — 已有块构建和渲染逻辑，只需扩展数据源和块顺序
- `AgentProfile.from_profile(loader, name)` — Profile 加载已完整实现

### Established Patterns
- @classmethod from_loader() — Phase 22-23 标准范式
- 叶依赖约束 — config/ 不导入框架其他模块，适配器模块可以导入 config/
- logger.warning() 碰撞提示 — 统一的 warning 模式
- 反转 discover 顺序 — project 覆盖 global
- Pydantic BaseModel — 所有配置模型
- barrel `__init__.py` 导出 — 带 `__all__` 列表

### Integration Points
- `backend/app/main.py` lifespan — ConfigLoader 和 backend Settings 的创建入口
- `backend/app/services/agent_factory.py` — 框架到应用的桥接层
- `framework/agent_framework/prompts/assembler.py` — prompt 组装的最终汇聚点
- STATE.md blocker "Backend circular import risk" — 实际无风险（backend → framework 单向依赖）

### Concerns
- **Backend Settings 字段映射** — backend 的 `llm_provider`/`llm_api_key`/`llm_model`/`llm_base_url` 与 framework Settings 的 `model`/`llm.*` 字段名不同，需要显式映射
- **PromptAssembler 块顺序变更** — 从现有的 SOUL → AGENTS_RULES → ... 变为 USER_PROVIDED → RULES → SOUL → ... ，可能影响现有测试

</code_context>

<specifics>
## Specific Ideas

- Backend Config 集成思路：
  ```python
  # main.py lifespan
  config_loader = ConfigLoader()  # 框架配置
  backend_settings = Settings()   # backend pydantic-settings
  factory = AgentFactory.from_configloader(config_loader, backend_settings)
  ```

- AgentFactory.from_configloader() 思路：
  ```python
  @classmethod
  def from_configloader(cls, loader: ConfigLoader, backend_settings: BackendSettings) -> AgentFactory:
      adapter = create_adapter(backend_settings.llm_provider, ...)
      skill_registry = SkillRegistry.from_loader(loader)
      hook_manager = HookManager.from_loader(loader)
      command_dispatcher = CommandDispatcher.from_loader(loader)
      agent_configs = AgentConfig.from_loader(loader)
      mcp_manager = McpManager.from_loader(loader)
      permissions = PermissionPipeline.from_loader(loader, profile_name="default")
      # 组装 ToolRouter, AgentLoop 等
      ...
  ```

- PromptAssembler.assemble() 新签名：
  ```python
  def assemble(self, loader: ConfigLoader, profile: AgentProfile, context_path: Path | None = None) -> list[PromptBlock]:
      user_provided = loader.load_agents_md()      # <user-provided>
      rules = RuleLoader.load_rules(loader, context_path)  # <rules>
      # 然后按设计文档顺序构建完整块列表
      ...
  ```

- RuleLoader 思路：
  ```python
  # framework/agent_framework/rules/loader.py
  class RuleLoader:
      @staticmethod
      def load_rules(loader: ConfigLoader, context_path: Path | None = None) -> str:
          """加载匹配的 rules 内容。"""
          paths = loader.discover("rules")
          all_rules = []
          for rules_dir in paths:
              for md_file in sorted(rules_dir.glob("*.md")):
                  frontmatter, body = parse_frontmatter(md_file.read_text())
                  rule_paths = frontmatter.get("paths")
                  if rule_paths is None or context_path is None:
                      all_rules.append(body)
                  elif any(fnmatch(str(context_path), p) for p in rule_paths):
                      all_rules.append(body)
          return "\n\n".join(all_rules)
  ```

- 叶依赖测试思路：
  ```python
  def test_config_is_leaf_dependency():
      """config/ 模块不应导入框架其他模块。"""
      import ast
      config_init = Path("framework/agent_framework/config/__init__.py")
      # 分析所有 config/ 文件的 import 语句
      # 断言没有 from agent_framework.{非config模块} 的导入
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-Backend Integration + E2E Wiring + Path-Scoped Rules*
*Context gathered: 2026-06-12*
