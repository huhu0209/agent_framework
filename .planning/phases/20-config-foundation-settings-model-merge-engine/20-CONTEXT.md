# Phase 20: Config Foundation — Settings Model + Merge Engine - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

构建 `framework/agent_framework/config/` 模块的核心数据基础：
1. **Settings Pydantic 模型**（CFG-03）— 定义全局运行时配置的统一 schema，嵌套子模型结构
2. **_merge_settings() 合并函数**（CFG-02）— 类型感知的多层配置合并，支持标量覆盖、对象浅合并、数组并集去重保序
3. **环境变量覆盖**（CFG-06）— APP_* 前缀 + `__` 分隔符覆盖标量 Settings 字段

纯新增代码，不修改任何现有文件。config/ 模块作为叶依赖，不导入框架其他模块。所有 1002 现有测试必须通过。

</domain>

<decisions>
## Implementation Decisions

### Settings 模型结构
- **D-01:** Settings 使用嵌套子模型 — `LlmConfig`、`ServerConfig`、`LoggingConfig`、`PermissionsConfig`。与 JSON 结构自然对应，合并函数可递归处理每层
- **D-02:** Settings 仅包含跨模块全局运行时配置（model, llm, server, logging, permissions）。各模块配置（agents、skills、hooks 等）通过 Phase 21 的 `discover()` 独立发现，不在 Settings 中
- **D-03:** `model` 字段放在顶层 + `llm` 子模型包含 `provider`/`api_key`/`base_url`。与设计文档 JSON 结构一致，`model` 顶层方便快速访问

### 合并引擎语义
- **D-04:** 数组合并顺序 — 低优先级在前、高优先级在后，去重保序。例如 global `["a"]` + project `["b"]` → `["a", "b"]`
- **D-05:** 去重标准 — 严格字符串全等。`"Bash(git *)"` == `"Bash(git *)"` 但 ≠ `"bash(git *)"`
- **D-06:** `_merge_settings()` 仅处理 `list[str]` 数组。Settings 中所有数组字段（permissions.allow/deny、cors_origins）都是字符串列表。对象列表合并（如 mcp_servers）留给 Phase 23

### 文件布局
- **D-07:** Phase 20 创建 3 个文件（最小文件集）：
  - `config/__init__.py` — barrel 导出
  - `config/settings.py` — Settings + 嵌套子模型（LlmConfig、ServerConfig、LoggingConfig、PermissionsConfig）
  - `config/merge.py` — `merge_settings()` 函数
  - loader.py 和 discovery.py 留到 Phase 21 创建，避免空桩文件

### Claude's Discretion
- Settings 子模型的具体字段定义和默认值（遵循设计文档 JSON 草案）
- `merge_settings()` 的函数签名、错误处理（类型不一致时 warning 还是 error）
- 环境变量覆盖的具体 Pydantic ConfigDict 配置
- 测试文件组织和测试用例设计

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 设计文档（核心参考）
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整的路径机制设计：目录结构、配置优先级、合并规则、Settings 结构草案、模块发现机制、迁移路径

### 需求定义
- `.planning/REQUIREMENTS.md` — CFG-02（合并策略）、CFG-03（Settings 模型）、CFG-06（环境变量覆盖）需求定义
- `.planning/ROADMAP.md` — Phase 20 目标、成功标准、范围定义

### 已有关联代码（参考，不修改）
- `backend/app/config/__init__.py` — 现有 pydantic_settings BaseSettings（4 字段，APP_ 前缀），Phase 24 集成时参考
- `framework/agent_framework/agents/config.py` — AgentConfig dataclass + load_agent_configs()，Phase 23 适配器参考
- `framework/agent_framework/tools/mcp/config.py` — McpManager + McpServerConfig(BaseModel)，Phase 23 适配器参考

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Pydantic 模型惯例、不可变模式、docstring 中文描述
- `.planning/codebase/ARCHITECTURE.md` — 框架层次、叶依赖约束

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pydantic >=2.0.0` — 已是框架核心依赖，Settings 直接继承 BaseModel
- `Pydantic ConfigDict` — 支持 `env_prefix`、`env_nested_delimiter` 等环境变量配置
- `SecretStr` — 已在 backend 使用，框架层 LlmConfig.api_key 可参考
- `@dataclass(frozen=True)` 模式 — config/ 模块如果需要不可变配置对象可参考

### Established Patterns
- Pydantic BaseModel for config — `McpServerConfig(BaseModel)`、`AgentProfile(BaseModel)` 等，Settings 遵循相同模式
- 模块级中文 docstring — `"""模块用途描述。"""`
- barrel `__init__.py` 导出 — 带 `__all__` 列表
- 叶依赖约束 — config/ 不导入框架其他模块（类似 llm/types.py 只依赖 pydantic）

### Integration Points
- Phase 21 的 ConfigLoader 将调用 `merge_settings()` 合并多级 settings.json
- Phase 21 的 ConfigLoader 将调用 `Settings(**merged_dict)` 创建最终 Settings 对象
- Phase 24 的 backend 集成将从 ConfigLoader 获取 Settings 替换现有 BaseSettings

</code_context>

<specifics>
## Specific Ideas

- Settings 结构草案（来自设计文档）：
  ```json
  {
    "model": "claude-sonnet-4-6-20250514",
    "llm": {"provider": "anthropic", "api_key": "", "base_url": null},
    "server": {"host": "0.0.0.0", "port": 30002, "cors_origins": ["http://localhost:30001"]},
    "logging": {"level": "info"},
    "permissions": {"allow": [], "deny": [], "ask": []}
  }
  ```
- `merge_settings(*dicts: dict)` 签名 — 接受多个 dict（从低到高优先级），返回合并后的 dict
- 环境变量覆盖：`APP_MODEL=xxx` 覆盖 `model`，`APP_LLM__PROVIDER=openai` 覆盖 `llm.provider`
- 测试重点：合并边界情况（空 dict、类型不一致、深层嵌套、数组去重、默认值）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-Config Foundation — Settings Model + Merge Engine*
*Context gathered: 2026-06-11*
