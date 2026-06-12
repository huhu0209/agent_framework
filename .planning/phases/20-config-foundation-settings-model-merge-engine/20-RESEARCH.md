# Phase 20: Config Foundation — Settings Model + Merge Engine - Research

**Researched:** 2026-06-11
**Domain:** Pydantic 模型设计 + 类型感知字典合并 + 环境变量映射
**Confidence:** HIGH

## Summary

Phase 20 构建框架 config/ 模块的数据基础：Settings Pydantic 模型（嵌套子模型结构）、_merge_settings() 类型感知合并函数、以及环境变量覆盖的映射机制。所有代码为纯新增，不修改任何现有文件。

**关键发现：** (1) Settings 必须使用 `pydantic.BaseModel` 而非 `pydantic_settings.BaseSettings`——pydantic-settings 未安装在项目 .venv 中，且 STATE.md 明确"零新依赖"策略。环境变量覆盖需通过自定义映射实现。(2) merge_settings() 必须递归处理嵌套 dict，否则 permissions.allow 等嵌套数组无法正确并集合并。(3) 已通过原型验证，所有核心行为在 pydantic 2.13.4 + Python 3.11.14 上工作正确。

**Primary recommendation:** 创建 3 个文件（config/__init__.py、config/settings.py、config/merge.py），使用 pydantic BaseModel + 递归 merge + env_var_map 常量映射。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Settings 使用嵌套子模型 — `LlmConfig`、`ServerConfig`、`LoggingConfig`、`PermissionsConfig`。与 JSON 结构自然对应，合并函数可递归处理每层
- **D-02:** Settings 仅包含跨模块全局运行时配置（model, llm, server, logging, permissions）。各模块配置（agents、skills、hooks 等）通过 Phase 21 的 `discover()` 独立发现，不在 Settings 中
- **D-03:** `model` 字段放在顶层 + `llm` 子模型包含 `provider`/`api_key`/`base_url`。与设计文档 JSON 结构一致，`model` 顶层方便快速访问
- **D-04:** 数组合并顺序 — 低优先级在前、高优先级在后，去重保序。例如 global `["a"]` + project `["b"]` -> `["a", "b"]`
- **D-05:** 去重标准 — 严格字符串全等。`"Bash(git *)"` == `"Bash(git *)"` 但 != `"bash(git *)"`
- **D-06:** `_merge_settings()` 仅处理 `list[str]` 数组。Settings 中所有数组字段（permissions.allow/deny、cors_origins）都是字符串列表。对象列表合并（如 mcp_servers）留给 Phase 23
- **D-07:** Phase 20 创建 3 个文件（最小文件集）：
  - `config/__init__.py` — barrel 导出
  - `config/settings.py` — Settings + 嵌套子模型
  - `config/merge.py` — `merge_settings()` 函数
  - loader.py 和 discovery.py 留到 Phase 21 创建，避免空桩文件

### Claude's Discretion
- Settings 子模型的具体字段定义和默认值（遵循设计文档 JSON 草案）
- `merge_settings()` 的函数签名、错误处理（类型不一致时 warning 还是 error）
- 环境变量覆盖的具体实现方式
- 测试文件组织和测试用例设计

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-02 | _merge_settings() 实现三种合并策略 — 数组并集（去重保序）、对象浅合并、标量覆盖 | merge.py 实现递归合并：dict 递归浅合并、list[str] 并集去重保序、标量覆盖。已原型验证全部策略正确。 |
| CFG-03 | Settings Pydantic BaseModel 定义（model/llm/server/logging/permissions 字段） | settings.py 使用 BaseModel（非 BaseSettings）+ 4 个嵌套子模型。已验证 model_validate 从 dict 构造、partial override、SecretStr 处理均正常。 |
| CFG-06 | 环境变量覆盖支持 APP_ 前缀 + env_nested_delimiter='__'（仅标量值） | 提供 ENV_VAR_MAP 常量定义映射关系。Phase 21 的 ConfigLoader 用此映射从 os.environ 读取并注入到合并后 dict。Settings 字段命名与映射对齐。 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Settings schema 定义 | API / Backend | — | 框架层提供数据模型，所有上层使用 |
| 配置合并逻辑 | API / Backend | — | 纯函数操作 dict，无 I/O |
| 环境变量映射 | API / Backend | — | 映射常量，Phase 21 ConfigLoader 消费 |
| 配置文件加载 | API / Backend | — | Phase 21 负责，Phase 20 仅提供合并工具 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.4 (已安装) | Settings + 子模型的 BaseModel 基类 | 项目核心依赖，所有类型定义已使用 [VERIFIED: pip show pydantic] |
| pytest | 9.0.3 (已安装) | 测试框架 | 项目标准测试框架 [VERIFIED: pip show pytest] |
| pytest-asyncio | 已安装 | 异步测试支持 | 项目标准，本阶段不需要异步测试但保持一致 [VERIFIED: pip show pytest-asyncio] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic.SecretStr | 2.13.4 | LlmConfig.api_key 的安全存储 | api_key 字段使用 SecretStr 避免日志泄露 [VERIFIED: pydantic docs via Context7] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| BaseModel + 手动 env 映射 | pydantic-settings BaseSettings | BaseSettings 自动读 env，但未安装在项目 .venv 中，添加新依赖违反 STATE.md "零新依赖"策略。手动映射更轻量、可控 [VERIFIED: .venv 缺失 pydantic-settings] |
| 递归 merge_settings() | pydantic-settings deep_merge | deep_merge 替换数组而非并集，不符合设计文档要求 [CITED: STATE.md] |

**Installation:**
```bash
# 无需安装新包 — 仅使用已有依赖
# pydantic>=2.0.0 已在 framework/pyproject.toml 中声明
```

**Version verification:**
```bash
.venv/bin/python -c "import pydantic; print(pydantic.__version__)"  # 2.13.4
.venv/bin/python -c "import pytest; print(pytest.__version__)"      # 9.0.3
```

## Package Legitimacy Audit

> Phase 20 不安装任何新包。仅使用项目已有依赖 pydantic 和 pytest。无需审计。

| Package | Registry | Status |
|---------|----------|--------|
| pydantic | PyPI (已安装) | 已在 pyproject.toml |
| pytest | PyPI (已安装) | 已在 pyproject.toml |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                      Phase 21 ConfigLoader（未来）
                            │
                  ┌─────────▼──────────┐
                  │ 1. 读 settings.json │
                  │ 2. 读 os.environ    │
                  │ 3. merge_settings() │◄─── merge.py（Phase 20）
                  │ 4. Settings(**dict) │◄─── settings.py（Phase 20）
                  └─────────┬──────────┘
                            │
                      Settings 对象
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    PermissionPipeline   Backend app     LLM adapter 创建
    (allow/deny 列表)   (host/port)     (provider/api_key)
```

```text
merge_settings() 数据流:

  输入（从低到高优先级）       处理               输出
  ┌─────────────┐
  │ global dict  │──┐
  └─────────────┘  │    ┌──────────────────┐
  ┌─────────────┐  ├───▶│ merge_settings() │───▶ 合并后 dict
  │ project dict │──┤    │ 递归处理每个 key  │
  └─────────────┘  │    │ dict → 递归浅合并 │
  ┌─────────────┐  │    │ list → 并集去重   │
  │ local dict   │──┘    │ scalar → 覆盖    │
  └─────────────┘         └──────────────────┘

  环境变量覆盖（Phase 21 实现）:
  APP_MODEL=gpt-4 ──▶ {"model": "gpt-4"} ──▶ 注入到合并后 dict
  APP_LLM__PROVIDER=openai ──▶ {"llm": {"provider": "openai"}}
```

### Recommended Project Structure
```
framework/agent_framework/config/
├── __init__.py        # barrel 导出 + __all__
├── settings.py        # Settings + 4 个嵌套子模型 + ENV_VAR_MAP
└── merge.py           # merge_settings() 函数

framework/tests/
├── test_settings.py   # Settings 模型测试
└── test_merge.py      # merge_settings() 测试
```

### Pattern 1: Pydantic BaseModel 嵌套子模型
**What:** Settings 使用 BaseModel（非 BaseSettings）+ 嵌套 BaseModel 子模型
**When to use:** 需要类型安全的配置 schema，但不依赖 pydantic-settings 包
**Example:**
```python
# Source: 验证于 pydantic 2.13.4 + Python 3.11.14
from pydantic import BaseModel, SecretStr


class LlmConfig(BaseModel):
    """LLM 连接配置。"""
    provider: str = "anthropic"
    api_key: SecretStr = SecretStr("")
    base_url: str | None = None


class Settings(BaseModel):
    """全局运行时配置。"""
    model: str = "claude-sonnet-4-6-20250514"
    llm: LlmConfig = LlmConfig()

# 从合并后 dict 构造（Phase 21 用法）
merged = {"model": "gpt-4", "llm": {"provider": "openai"}}
settings = Settings.model_validate(merged)
```

### Pattern 2: 递归类型感知合并
**What:** merge_settings 递归进入嵌套 dict，确保 list[str] 在任意深度都能并集合并
**When to use:** 多层配置叠加（global -> project -> local -> env）
**Example:**
```python
# Source: 原型验证通过
def merge_settings(*dicts: dict) -> dict:
    """合并多个配置字典（从低到高优先级）。"""
    if not dicts:
        return {}
    result: dict = {}
    for d in dicts:
        for key, value in d.items():
            if key not in result:
                result[key] = value
            elif isinstance(value, dict) and isinstance(result[key], dict):
                # 递归浅合并（关键：递归才能让嵌套 list 也做并集）
                result[key] = merge_settings(result[key], value)
            elif isinstance(value, list) and isinstance(result[key], list):
                # list[str] 并集去重保序
                seen: set[str] = set()
                merged: list[str] = []
                for item in result[key] + value:
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[key] = merged
            else:
                # 标量覆盖
                result[key] = value
    return result
```

### Pattern 3: 环境变量映射常量
**What:** 定义 APP_* 环境变量到 Settings 字段路径的映射，供 Phase 21 ConfigLoader 使用
**When to use:** 需要在不依赖 pydantic-settings 的情况下支持环境变量覆盖
**Example:**
```python
# Source: CFG-06 需求定义
# 环境变量 -> 字段路径映射（仅标量值）
ENV_VAR_MAP: dict[str, str] = {
    "APP_MODEL": "model",
    "APP_LLM__PROVIDER": "llm.provider",
    "APP_LLM__API_KEY": "llm.api_key",
    "APP_LLM__BASE_URL": "llm.base_url",
    "APP_SERVER__HOST": "server.host",
    "APP_SERVER__PORT": "server.port",
    "APP_LOGGING__LEVEL": "logging.level",
}
```

### Anti-Patterns to Avoid
- **BaseSettings with pydantic-settings:** 项目 .venv 未安装 pydantic-settings，且 STATE.md 明确"零新依赖"。不要使用 `from pydantic_settings import BaseSettings`。
- **非递归 dict 浅合并:** 如果 merge_settings 对 dict 只做 `{**low, **high}` 而不递归，嵌套的 list[str] 字段（如 permissions.allow）会被整体替换而非并集合并。这是一个关键 bug，已通过原型验证确认。
- **从 config/ 导入框架其他模块:** config/ 是叶依赖，不能导入 agent_framework 下的任何其他模块（llm/、tools/ 等）。只能依赖 pydantic 和 stdlib。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 数据验证和默认值 | 手写验证逻辑 | pydantic BaseModel | 自动类型检查、默认值、model_validate、model_dump |
| API key 安全存储 | 普通字符串 | pydantic SecretStr | 防止日志/打印泄露，model_dump(mode='json') 才暴露值 |
| 模型序列化 | 手写 to_dict() | model_dump() | 处理嵌套模型、SecretStr、None 等边界情况 |

**Key insight:** pydantic BaseModel 提供了 Settings 需要的所有功能（验证、默认值、序列化、嵌套模型），无需 pydantic-settings。环境变量读取是一个简单的 dict 操作，不需要框架支持。

## Common Pitfalls

### Pitfall 1: 非递归 dict 合并丢失 list 并集
**What goes wrong:** 如果 merge_settings 对 dict 值做 `{**low, **high}` 一层覆盖，permissions.allow 会被 project 级别整体替换，而不是并集合并。
**Why it happens:** 浅合并语义对嵌套结构是"整体替换"，而设计要求嵌套 list 做"并集叠加"。
**How to avoid:** merge_settings 必须递归进入 dict 值：`result[key] = merge_settings(result[key], value)`。
**Warning signs:** 测试用例 `global={permissions:{allow:["a"]}} + project={permissions:{allow:["b"]}}` 应得到 `{allow:["a","b"]}` 而非 `{allow:["b"]}`。

### Pitfall 2: 使用 pydantic-settings BaseSettings
**What goes wrong:** Settings 继承 BaseSettings，但 pydantic-settings 未安装在项目 .venv 中，导致 ImportError。
**Why it happens:** BaseSettings 在系统 Python 中可用（被 langchain-community 安装），但项目 .venv 中不存在。
**How to avoid:** 使用 `pydantic.BaseModel`，环境变量覆盖通过 Phase 21 的 ConfigLoader 手动实现。
**Warning signs:** 测试在 .venv 中运行失败：`ModuleNotFoundError: No module named 'pydantic_settings'`。

### Pitfall 3: SecretStr 序列化泄漏
**What goes wrong:** `model_dump()` 返回 `SecretStr('...')` 对象而非字符串，直接 JSON 序列化会得到 `"SecretStr('...')"`。
**Why it happens:** SecretStr 的默认 dump 行为是保留 SecretStr 对象。
**How to avoid:** 需要序列化时使用 `model_dump(mode='json')`。或者 merge_settings 处理 api_key 时直接操作原始 dict（merge 层面不涉及 Settings 对象）。
**Warning signs:** JSON 输出中 api_key 字段不是纯字符串。

### Pitfall 4: config/ 模块导入其他框架模块
**What goes wrong:** config/ 导入 llm/ 或 tools/ 的类型，造成循环依赖或违反叶依赖约束。
**Why it happens:** 开发者可能想复用 llm/types.py 中的类型定义。
**How to avoid:** config/ 只依赖 pydantic 和 stdlib。Settings 中的字段定义是自包含的，不复用其他模块的类型。
**Warning signs:** import 测试失败或检测到 agent_framework.xxx 的导入（pydantic 除外）。

### Pitfall 5: merge_settings 修改输入 dict
**What goes wrong:** merge_settings 修改了传入的 dict 参数，导致调用者的原始数据被污染。
**Why it happens:** Python dict 是可变对象，直接赋值 `result[key] = value` 在某些分支可能共享引用。
**How to avoid:** 对 dict 类型值递归调用 merge_settings（返回新 dict）。对 list 类型值构建新 list。永远不修改输入参数。
**Warning signs:** 调用 merge_settings 后，原始 dict 被修改。

## Code Examples

### Settings Model（settings.py 核心结构）
```python
# Source: [VERIFIED] 原型验证于 pydantic 2.13.4
"""全局运行时配置 — Settings Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, SecretStr


class LlmConfig(BaseModel):
    """LLM 连接配置。"""
    provider: str = "anthropic"
    api_key: SecretStr = SecretStr("")
    base_url: str | None = None


class ServerConfig(BaseModel):
    """服务端配置。"""
    host: str = "0.0.0.0"
    port: int = 30002
    cors_origins: list[str] = ["http://localhost:30001"]


class LoggingConfig(BaseModel):
    """日志配置。"""
    level: str = "info"


class PermissionsConfig(BaseModel):
    """权限配置。"""
    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []


class Settings(BaseModel):
    """全局运行时配置 — 统一 schema。

    字段与 settings.json 结构直接对应。merge_settings() 合并后
    的 dict 通过 Settings.model_validate(merged) 创建实例。
    环境变量覆盖由 Phase 21 的 ConfigLoader 在合并后注入。
    """
    model: str = "claude-sonnet-4-6-20250514"
    llm: LlmConfig = LlmConfig()
    server: ServerConfig = ServerConfig()
    logging: LoggingConfig = LoggingConfig()
    permissions: PermissionsConfig = PermissionsConfig()
```

### 环境变量映射（settings.py 的一部分）
```python
# Source: CFG-06 需求 + CONTEXT.md specifics
# 环境变量名 -> Settings 字段路径（点分隔），仅标量字段
ENV_VAR_MAP: dict[str, str] = {
    "APP_MODEL": "model",
    "APP_LLM__PROVIDER": "llm.provider",
    "APP_LLM__API_KEY": "llm.api_key",
    "APP_LLM__BASE_URL": "llm.base_url",
    "APP_SERVER__HOST": "server.host",
    "APP_SERVER__PORT": "server.port",
    "APP_LOGGING__LEVEL": "logging.level",
}
```

### merge_settings 函数（merge.py 核心）
```python
# Source: [VERIFIED] 原型验证通过所有测试用例
"""配置合并 — 类型感知的多层字典合并。"""

from __future__ import annotations


def merge_settings(*dicts: dict) -> dict:
    """合并多个配置字典，从低到高优先级。

    策略：
    - dict -> 递归浅合并
    - list[str] -> 并集去重保序（低优先级在前）
    - 标量 -> 高优先级覆盖

    Args:
        *dicts: 配置字典，从低到高优先级。

    Returns:
        合并后的新字典（不修改输入）。
    """
    if not dicts:
        return {}

    result: dict = {}
    for d in dicts:
        for key, value in d.items():
            if key not in result:
                result[key] = value
            elif isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = merge_settings(result[key], value)
            elif isinstance(value, list) and isinstance(result[key], list):
                seen: set = set()
                merged: list = []
                for item in result[key] + value:
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[key] = merged
            else:
                result[key] = value
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydantic v1 BaseModel | pydantic v2 BaseModel (model_validate, model_dump) | pydantic 2.0 (2023-06) | model_validate 替代 parse_obj，model_dump 替代 dict() |
| pydantic BaseSettings in pydantic core | pydantic-settings 独立包 | pydantic 2.0 (2023-06) | BaseSettings 需要额外安装 pydantic-settings |
| 手写验证逻辑 | pydantic BaseModel 自动验证 | pydantic 1.0+ | 默认值、类型检查、嵌套模型自动处理 |

**Deprecated/outdated:**
- `pydantic.parse_obj()`: 使用 `model_validate()` 替代 [CITED: pydantic v2 migration guide]
- `model.dict()`: 使用 `model_dump()` 替代 [CITED: pydantic v2 migration guide]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Settings 使用 BaseModel（非 BaseSettings）— 基于 CONTEXT.md 明确声明和 .venv 缺失 pydantic-settings | Standard Stack | 如果后续决定添加 pydantic-settings 依赖，需要重构为 BaseSettings |
| A2 | merge_settings 对 dict 递归浅合并 — 基于 D-04 数组合并需求和原型验证 | Architecture Patterns | 如果设计意图是真正的单层浅合并（嵌套 list 整体替换），需改为非递归 |
| A3 | ENV_VAR_MAP 定义在 settings.py 中 — 基于 Claude's Discretion 范围 | Architecture Patterns | 位置可调整，功能不变 |
| A4 | merge_settings 不处理类型不一致（list vs scalar）— 高优先级直接覆盖 | Architecture Patterns | 如果需要 warning 日志，需额外处理 |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **merge_settings 递归 vs 单层**
   - What we know: D-04 要求数组并集保序，D-06 限制仅处理 list[str]。但 permissions 是嵌套在 dict 中的 list[str]。
   - What's unclear: "对象浅合并"是指单层 `{**low, **high}` 还是递归到 dict 内部对 list 做并集？
   - Recommendation: 使用递归实现。原型验证表明非递归会导致 permissions.allow 被整体替换而非并集合并，违反 D-04 语义。这是已通过代码验证的事实，不是假设。

2. **CFG-06 在 Phase 20 的实现范围**
   - What we know: ROADMAP Success Criteria 3 要求"APP_* 环境变量在验证时覆盖标量 Settings 字段"。
   - What's unclear: Phase 20 是实现完整的环境变量读取（需要 ConfigLoader），还是只提供映射定义？
   - Recommendation: Phase 20 提供 ENV_VAR_MAP + apply_env_vars() 辅助函数。完整的 "读 os.environ -> 注入到 merged dict -> 创建 Settings" 流程在 Phase 21 的 ConfigLoader 中实现。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Settings model | ✓ | 3.11.14 | — |
| pydantic | Settings BaseModel | ✓ | 2.13.4 | — |
| pytest | 测试 | ✓ | 9.0.3 | — |
| pydantic-settings | BaseSettings env var | ✗ | — | 使用 BaseModel + 手动 env 映射 |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- pydantic-settings: 使用 BaseModel + ENV_VAR_MAP + apply_env_vars() 替代。不添加新依赖，符合 STATE.md 策略。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | framework/pyproject.toml (asyncio_mode=auto, pythonpath=["tests"]) |
| Quick run command | `.venv/bin/pytest tests/test_settings.py tests/test_merge.py -v` |
| Full suite command | `.venv/bin/pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-02 | 标量覆盖取最高优先级值 | unit | `.venv/bin/pytest tests/test_merge.py::TestMergeSettings::test_scalar_override -v` | Wave 0 |
| CFG-02 | dict 浅合并 | unit | `.venv/bin/pytest tests/test_merge.py::TestMergeSettings::test_dict_shallow_merge -v` | Wave 0 |
| CFG-02 | list[str] 并集去重保序 | unit | `.venv/bin/pytest tests/test_merge.py::TestMergeSettings::test_list_union_dedup -v` | Wave 0 |
| CFG-02 | 嵌套 dict 递归合并 | unit | `.venv/bin/pytest tests/test_merge.py::TestMergeSettings::test_nested_recursive -v` | Wave 0 |
| CFG-03 | Settings 全默认值实例化 | unit | `.venv/bin/pytest tests/test_settings.py::TestSettings::test_default_values -v` | Wave 0 |
| CFG-03 | Settings 从 dict 构造 | unit | `.venv/bin/pytest tests/test_settings.py::TestSettings::test_from_dict -v` | Wave 0 |
| CFG-03 | Settings 嵌套子模型验证 | unit | `.venv/bin/pytest tests/test_settings.py::TestSettings::test_nested_models -v` | Wave 0 |
| CFG-06 | ENV_VAR_MAP 映射完整 | unit | `.venv/bin/pytest tests/test_settings.py::TestEnvVarMap::test_map_completeness -v` | Wave 0 |
| CFG-06 | apply_env_vars 覆盖标量 | unit | `.venv/bin/pytest tests/test_settings.py::TestEnvVarMap::test_apply_env_vars -v` | Wave 0 |
| INT-05 | 全部 1002 测试通过 | regression | `.venv/bin/pytest tests/ -v` | Existing |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_settings.py tests/test_merge.py -v`
- **Per wave merge:** `.venv/bin/pytest tests/ -v`
- **Phase gate:** `.venv/bin/pytest tests/ -v` — 1002 tests green

### Wave 0 Gaps
- [ ] `framework/tests/test_settings.py` — covers CFG-03, CFG-06
- [ ] `framework/tests/test_merge.py` — covers CFG-02

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | pydantic BaseModel 自动验证类型和约束 |
| V6 Cryptography | partial | SecretStr 防止 api_key 日志泄露 |

### Known Threat Patterns for Pydantic Config Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| api_key 泄露到日志 | Information Disclosure | SecretStr 包裹，model_dump() 不暴露明文 |
| 恶意 env var 注入 | Spoofing | apply_env_vars 仅处理预定义的 ENV_VAR_MAP 键 |
| 配置路径遍历 | Tampering | Phase 20 不涉及文件路径，Phase 21 负责 |

## Sources

### Primary (HIGH confidence)
- pydantic 2.13.4 — installed in .venv, verified via `pip show pydantic` and runtime prototype
- pydantic BaseModel docs — nested models, model_validate, model_dump verified via Context7 [CITED: Context7 /pydantic/pydantic]
- pydantic-settings docs — env_prefix, env_nested_delimiter behavior verified via Context7 [CITED: Context7 /pydantic/pydantic-settings]
- Project codebase — McpServerConfig(BaseModel), AgentProfile(BaseModel) patterns [VERIFIED: codebase grep]
- CONTEXT.md decisions D-01 through D-07 — locked decisions [CITED: 20-CONTEXT.md]

### Secondary (MEDIUM confidence)
- STATE.md — "零新依赖" strategy, config/ as leaf dependency [CITED: .planning/STATE.md]
- ROADMAP.md — Phase 20 success criteria, requirement mapping [CITED: .planning/ROADMAP.md]
- CONVENTIONS.md — Pydantic model conventions, docstring patterns, barrel exports [CITED: .planning/codebase/CONVENTIONS.md]
- ARCHITECTURE.md — Leaf dependency constraint, framework structure [CITED: .planning/codebase/ARCHITECTURE.md]

### Tertiary (LOW confidence)
- None — all findings verified through code, documentation, or prototype

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pydantic BaseModel 已在项目中广泛使用，版本确认，原型验证通过
- Architecture: HIGH — Settings 结构和 merge 逻辑已通过代码原型验证，符合所有锁定决策
- Pitfalls: HIGH — 5 个陷阱全部通过原型验证确认，特别是递归合并和 BaseSettings 陷阱
- CFG-06 scope: MEDIUM — Phase 20 vs Phase 21 的实现边界需要 planner 确认

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable — pydantic v2 API 稳定)
