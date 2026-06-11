# Phase 21: Discovery + Loader + AGENTS.md Chain - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

完成 `framework/agent_framework/config/` 模块的核心加载能力：
1. **ConfigLoader 入口类**（CFG-01）— 层级加载 settings.json（global → project → local → env）并创建 Settings 实例
2. **discover_paths() 路径发现**（CFG-04）— 按优先级返回模块目录路径列表
3. **模块类型发现**（CFG-05）— 支持 8 种模块类型（skills/agents/commands/hooks/rules/profiles/memory/mcp）的统一发现
4. **AGENTS.md 指令链加载**（INS-01, INS-02, INS-05）— 从全局到项目到父目录链的完整指令拼接
5. **Profile 加载**（INS-04）— 从全局 + 项目路径加载指定 profile 目录

纯新增代码，不修改任何现有文件。config/ 模块保持叶依赖。所有 1002 现有测试必须通过。

</domain>

<decisions>
## Implementation Decisions

### ConfigLoader 接口设计
- **D-01:** `load_settings()` 无缓存，每次调用重新加载文件、合并、实例化 Settings
- **D-02:** `discover(module_name)` 返回纯 `list[Path]`，按优先级从低到高排列。调用方自行遍历
- **D-03:** `settings.local.json` 自动尝试读取（与 project settings 同目录），不存在则跳过
- **D-04:** ConfigLoader 构造函数用带默认值的可选参数 — `ConfigLoader(global_dir: Path = Path.home(), project_dir: Path = Path.cwd())`。对外零参数即可，测试时可传入 tmp_path

### AGENTS.md 链加载细节
- **D-05:** 父目录链遍历仅识别 `.git/` 作为终止边界，不支持其他 VCS 标记
- **D-06:** 父目录链从 `.git/` 根目录向下遍历到 CWD。越靠近 CWD 的文件后加载（隐含覆盖优先级越高）
- **D-07:** 任一层级的文件缺失时静默跳过，无 warning 也无 debug 日志
- **D-08:** 多个 AGENTS.md 文件拼接时，每个片段前加 `# Source: <path>` 标题标注来源，片段间用双换行分隔。path 使用相对于运行上下文的可读路径（如 `~/.agent-framework/AGENTS.md`、`.agent-framework/AGENTS.md`、`../AGENTS.md`）

### Profile 加载策略
- **D-09:** profile 名称由调用方显式传入 `load_profile(name)`，不从 settings.json 读取。不修改 Settings 模型
- **D-10:** 同名 profile 先加载 global 目录的子文件，再用 project 目录的非空子文件覆盖。按字段独立合并（soul.md / agents.md / identity.md / tool_guidance.md 各自独立覆盖，非空覆盖为空）
- **D-11:** profile 子文件缺失时跳过，字段留空。复用已有 `_read_file()` 逻辑

### discover_paths 路径解析
- **D-12:** 8 种模块类型使用硬编码映射表 `MODULE_DIRS: dict[str, str]`，module_name → 子目录名。新增类型时修改映射表
- **D-13:** 目录不存在时静默跳过，只返回存在的路径。调用方拿到空列表时自然处理
- **D-14:** 测试时用 tmp_path 构建 mock 目录结构，通过 ConfigLoader 可选参数传入

### Claude's Discretion
- 具体的 `MODULE_DIRS` 映射表内容（与设计文档目录结构对应即可）
- `load_settings()` 内部文件读取的 error handling 策略（文件存在但 JSON 格式错误时 raise 还是 warning + 跳过）
- `load_agents_md()` 的返回类型和空结果处理
- `discover_paths()` 是否验证 module_name 在映射表中（未知名称 raise ValueError？）
- 测试文件组织和测试用例设计
- 新增文件的数量和命名（loader.py / discovery.py / instructions.py 等）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 设计文档（核心参考）
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整的路径机制设计：目录结构、配置优先级、合并规则、Settings 结构草案、模块发现机制、指令链加载顺序、Profile 加载

### 需求定义
- `.planning/REQUIREMENTS.md` — CFG-01（ConfigLoader 四级覆盖链）、CFG-04（discover_paths）、CFG-05（8 种模块类型发现）、INS-01（AGENTS.md 指令链）、INS-02（父目录链遍历）、INS-04（Profile 加载）、INS-05（load_agents_md 拼接）
- `.planning/ROADMAP.md` — Phase 21 目标、成功标准、范围定义、2 个 plan 拆分建议

### Phase 20 已实现代码（本 phase 在此基础上扩展）
- `framework/agent_framework/config/settings.py` — Settings 模型 + 嵌套子模型 + ENV_VAR_MAP + apply_env_vars()
- `framework/agent_framework/config/merge.py` — merge_settings() 合并函数
- `framework/agent_framework/config/__init__.py` — barrel 导出

### 已有关联代码（参考，不修改）
- `framework/agent_framework/prompts/profiles.py` — AgentProfile.from_directory() 从单目录加载 profile 的现有逻辑，Profile 加载需复用
- `framework/agent_framework/prompts/assembler.py` — PromptAssembler 的 block 组装逻辑，Phase 24 集成时参考
- `backend/app/config/__init__.py` — 现有 pydantic_settings BaseSettings（4 字段，APP_ 前缀），Phase 24 集成时参考
- `framework/agent_framework/agents/config.py` — AgentConfig dataclass + load_agent_configs()，Phase 22/23 适配器参考

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Pydantic 模型惯例、不可变模式、docstring 中文描述
- `.planning/codebase/ARCHITECTURE.md` — 框架层次、叶依赖约束

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `merge_settings(*dicts)` — Phase 20 已实现，ConfigLoader.load_settings() 直接调用合并多级 settings.json
- `apply_env_vars(merged, env)` — Phase 20 已实现，在合并后注入环境变量覆盖
- `Settings.model_validate(merged_dict)` — Pydantic 验证，从合并后的 dict 创建 Settings 实例
- `AgentProfile.from_directory(path)` — 已有从单目录加载 profile 的逻辑，discover 后可复用
- `_read_file(path)` — profiles.py 中的静默读文件工具函数，文件不存在返回空字符串

### Established Patterns
- Pydantic BaseModel for config — Settings 及嵌套子模型
- 叶依赖约束 — config/ 不导入框架其他模块（仅依赖 pydantic + 标准库 pathlib/json/os）
- barrel `__init__.py` 导出 — 带 `__all__` 列表
- 模块级中文 docstring — `"""模块用途描述。"""`
- Phase 20 文件组织 — 每个 concerns 一个文件（settings.py / merge.py），Phase 21 新增 loader.py / discovery.py

### Integration Points
- Phase 22 的 SkillRegistry.from_loader() 将调用 `loader.discover("skills")` 获取路径列表
- Phase 22 的 HookManager.from_loader() 将调用 `loader.discover("hooks")` 获取路径列表
- Phase 24 的 backend 集成将从 ConfigLoader 获取 Settings 替换现有 BaseSettings
- Phase 24 的 PromptAssembler 将集成 load_agents_md() 的指令链到 <user-provided> 块
- 现有 AgentProfile.from_directory() 在 Phase 23 将配合 discover("profiles") 使用

</code_context>

<specifics>
## Specific Ideas

- ConfigLoader.load_settings() 完整流程：
  1. 读取 `~/.agent-framework/settings.json`（global）
  2. 读取 `.agent-framework/settings.json`（project）
  3. 读取 `.agent-framework/settings.local.json`（local，gitignored）
  4. `merge_settings(global_dict, project_dict, local_dict)` 合并
  5. `apply_env_vars(merged, os.environ)` 注入环境变量
  6. `Settings.model_validate(final_dict)` 创建实例

- AGENTS.md 链拼接示例：
  ```
  # Source: ~/.agent-framework/AGENTS.md
  [全局指令内容]

  # Source: .agent-framework/AGENTS.md
  [项目指令内容]

  # Source: .agent-framework/AGENTS.local.md
  [个人项目指令内容]

  # Source: ../AGENTS.md
  [父目录指令内容]

  # Source: ~/.agent-framework/user.md
  [用户画像内容]
  ```

- Profile 加载示例：
  ```python
  loader = ConfigLoader()
  profile = loader.load_profile("default")
  # 先加载 ~/.agent-framework/profiles/default/ 的 soul.md, agents.md, ...
  # 再加载 .agent-framework/profiles/default/ 的同名文件覆盖非空字段
  ```

- discover_paths() 示例：
  ```python
  loader.discover_paths("skills")
  # → [Path("~/.agent-framework/skills"), Path(".agent-framework/skills")]
  # 仅返回存在的路径，不存在的跳过
  ```

- ROADMAP 建议拆分为 2 个 plan：
  - 21-01: discover_paths() + ConfigLoader core（CFG-01, CFG-04, CFG-05）
  - 21-02: AGENTS.md chain loader + Profile loading（INS-01, INS-02, INS-04, INS-05）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-Discovery + Loader + AGENTS.md Chain*
*Context gathered: 2026-06-11*
