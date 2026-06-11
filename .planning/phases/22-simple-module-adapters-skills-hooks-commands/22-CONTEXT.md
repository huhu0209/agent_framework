# Phase 22: Simple Module Adapters — Skills, Hooks, Commands - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

为 SkillRegistry、HookManager、CommandDispatcher 添加 `from_loader()` 工厂方法，使它们能从 ConfigLoader.discover() 发现的路径自动初始化。

本 phase 涉及 ADP-01、ADP-02、ADP-03、ADP-09 四个需求：
1. **SkillRegistry.from_loader(loader)** — 从 discover("skills") 路径创建注册表
2. **HookManager.from_loader(loader)** — 从 discover("hooks") 路径合并 hooks.json
3. **CommandDispatcher.from_loader(loader)** — 注入通过 from_loader 加载的 SkillRegistry
4. **向后兼容（ADP-09）** — 所有现有构造函数签名不变，工厂方法为纯新增 API

纯新增代码（工厂方法），不修改任何现有构造函数。所有 1002 现有测试必须通过。

</domain>

<decisions>
## Implementation Decisions

### Skill 名称碰撞策略
- **D-01:** `SkillRegistry.from_loader()` 在入口处将 `discover("skills")` 返回的 `[global, project]` 反转为 `[project, global]` 传入 `SkillRegistry.__init__(skills_dirs=...)`。现有 "first-found wins" 逻辑自然让 project 级别同名 skill 覆盖 global
- **D-02:** 名称碰撞时静默覆盖，不打印 warning 日志。与现有 SkillRegistry 行为保持一致

### Hook 合并语义
- **D-03:** `HookManager.from_loader()` 按 discover() 原序（global → project）分别调用 `load_from_json()`。先加载 global 的 hooks.json，再加载 project 的 hooks.json
- **D-04:** 项目级的 hook 追加到全局级的同 event 列表末尾。不同 event 独立，同 event 内按 matcher 分组，相同 matcher 的 hooks 数组拼接
- **D-05:** 加载顺序 = 触发顺序：global hook 先触发，project hook 后触发。符合"全局为基础，项目为增强"的语义

### Command 发现范围
- **D-06:** `CommandDispatcher.from_loader()` 仅负责：调用 `SkillRegistry.from_loader(loader)` 获取已加载的 SkillRegistry，再创建 `CommandDispatcher(skill_registry=skill_registry)`
- **D-07:** 不引入新的命令文件格式或目录扫描机制。discover("commands") 目录预留供未来扩展，当前不读取
- **D-08:** 命名保持与现有代码一致：使用 `CommandDispatcher`（非 ROADMAP 中的 "CommandRegistry"），from_loader() 为 @classmethod

### 加载失败容错策略
- **D-09:** 所有 from_loader() 统一采用 warning + 跳过策略。复用现有 SkillRegistry 和 HookManager 已有的容错模式，不在 from_loader() 层面增加额外容错逻辑
- **D-10:** Skill 解析失败时 SkillRegistry._parse_skill_document() 已返回空 manifest；Hook 无效条目 load_from_json() 已 warning 跳过。from_loader() 仅调用这些已有方法

### Claude's Discretion
- from_loader() 的具体实现方式（@classmethod 或模块级函数）—— 推荐 @classmethod，与其他模块一致
- hooks.json 不存在时的行为——静默跳过（目录存在但文件不存在时自然无 hook）
- SkillRegistry.from_loader() 是否需要在构造后立即调用 refresh()——由构造函数内部的 _full_refresh() 自动处理
- 测试文件组织和测试用例设计
- 新增文件命名：工厂方法代码放在现有模块文件内（registry.py / manager.py / dispatcher.py）还是单独文件

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 设计文档（核心参考）
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整的路径机制设计：模块发现机制、适配器设计意图

### 需求定义
- `.planning/REQUIREMENTS.md` — ADP-01（SkillRegistry.from_loader）、ADP-02（HookManager.from_loader）、ADP-03（CommandRegistry.from_loader）、ADP-09（向后兼容）
- `.planning/ROADMAP.md` — Phase 22 目标、成功标准、范围定义

### Phase 21 已实现代码（本 phase 直接依赖）
- `framework/agent_framework/config/loader.py` — ConfigLoader 类 + discover() 方法 + load_settings()
- `framework/agent_framework/config/settings.py` — Settings 模型
- `framework/agent_framework/config/__init__.py` — barrel 导出

### 本 phase 需修改/扩展的代码
- `framework/agent_framework/skills/registry.py` — SkillRegistry 类：添加 from_loader() @classmethod
- `framework/agent_framework/hooks/manager.py` — HookManager 类：添加 from_loader() @classmethod
- `framework/agent_framework/commands/dispatcher.py` — CommandDispatcher 类：添加 from_loader() @classmethod

### 参考代码（不修改）
- `framework/agent_framework/prompts/profiles.py` — AgentProfile.from_directory() 类似的目录加载模式
- `framework/agent_framework/agents/config.py` — AgentConfig + load_agent_configs()，Phase 23 适配器参考

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Pydantic 模型惯例、不可变模式、docstring 中文描述
- `.planning/codebase/ARCHITECTURE.md` — 框架层次、叶依赖约束

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigLoader.discover(module_name) -> list[Path]` — Phase 21 已实现，返回 [global, project] 优先级目录列表
- `SkillRegistry.__init__(skills_dirs: list[Path])` — 已接受 list[Path] 参数，from_loader() 只需反转顺序后传入
- `HookManager.load_from_json(path: Path)` — 已有单文件加载逻辑，from_loader() 复用此方法多次调用
- `CommandDispatcher.__init__(skill_registry: SkillRegistry | None)` — 已接受可选 SkillRegistry，from_loader() 传入加载后的实例

### Established Patterns
- @classmethod 工厂方法 — 与现有 `create_adapter()` 工厂函数模式类似，但作为类方法更符合 Python 惯例
- Additive API — v0.0.6 核心约束：不修改现有构造函数签名，from_loader() 为纯新增
- 叶依赖约束 — config/ 不导入框架其他模块，但适配器（skills/hooks/commands）可以导入 config/

### Integration Points
- Phase 23 的 AgentProfile.from_loader() 将复用相同的 from_loader() 模式，本 phase 建立范式
- Phase 24 的 backend 集成将通过 ConfigLoader + from_loader() 一键初始化所有模块
- config/ 模块的 `from __future__ import annotations` 和 Pydantic 模型已就绪

### Concerns
- **STATE.md Blocker "名称碰撞方向"** — 已解决：反转 discover 顺序
- **HookManager.trusted 参数** — from_loader() 需要决定 trusted 默认值。当前构造函数默认 False。建议 from_loader() 也默认 False，或从 settings 读取

</code_context>

<specifics>
## Specific Ideas

- SkillRegistry.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader) -> SkillRegistry:
      paths = loader.discover("skills")
      # 反转顺序：project 优先
      reversed_paths = list(reversed(paths))
      return cls(skills_dirs=reversed_paths)
  ```

- HookManager.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader, trusted: bool = False) -> HookManager:
      manager = cls(trusted=trusted)
      for hook_dir in loader.discover("hooks"):
          hook_file = hook_dir / "hooks.json"
          if hook_file.exists():
              manager.load_from_json(hook_file)
      return manager
  ```

- CommandDispatcher.from_loader() 实现思路：
  ```python
  @classmethod
  def from_loader(cls, loader: ConfigLoader) -> CommandDispatcher:
      skill_registry = SkillRegistry.from_loader(loader)
      return cls(skill_registry=skill_registry)
  ```

- ROADMAP 建议 2 个 plan：
  - 22-01: SkillRegistry.from_loader() + HookManager.from_loader() + CommandDispatcher.from_loader()（三个简单适配器）
  - 22-02 可能不需要，因为 3 个适配器逻辑都较简单，单 plan 可覆盖

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-Simple Module Adapters — Skills, Hooks, Commands*
*Context gathered: 2026-06-11*
