# Phase 21: Discovery + Loader + AGENTS.md Chain - Research

**Researched:** 2026-06-11
**Domain:** Config path discovery, instruction chain loading, profile loading
**Confidence:** HIGH

## Summary

Phase 21 在 Phase 20 已完成的 Settings 模型和 merge_settings() 合并引擎之上，构建 ConfigLoader 统一入口类。这个入口类提供三个核心能力：(1) 四级覆盖链加载 settings.json 并返回 Settings 实例；(2) 按模块类型发现全局和项目级目录路径；(3) 加载 AGENTS.md 指令链和 Profile 目录。所有代码为纯新增，不修改任何现有文件，config/ 模块保持叶依赖约束。

技术核心是 pathlib 路径操作和 JSON 文件读取——不引入任何新依赖。关键设计约束来自 CONTEXT.md 中的 14 个锁定决策和设计文档中定义的目录结构。代码复用 Phase 20 的 merge_settings() 和 apply_env_vars()，以及 prompts/profiles.py 的 _read_file() 模式。

**Primary recommendation:** 按 ROADMAP 建议拆分为 2 个 plan（21-01: discover + loader core, 21-02: AGENTS.md chain + profile），每个 plan 新增一个 .py 文件（loader.py / instructions.py）加对应测试文件。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `load_settings()` 无缓存，每次调用重新加载文件、合并、实例化 Settings
- **D-02:** `discover(module_name)` 返回纯 `list[Path]`，按优先级从低到高排列。调用方自行遍历
- **D-03:** `settings.local.json` 自动尝试读取（与 project settings 同目录），不存在则跳过
- **D-04:** ConfigLoader 构造函数用带默认值的可选参数 — `ConfigLoader(global_dir: Path = Path.home(), project_dir: Path = Path.cwd())`。对外零参数即可，测试时可传入 tmp_path
- **D-05:** 父目录链遍历仅识别 `.git/` 作为终止边界，不支持其他 VCS 标记
- **D-06:** 父目录链从 `.git/` 根目录向下遍历到 CWD。越靠近 CWD 的文件后加载（隐含覆盖优先级越高）
- **D-07:** 任一层级的文件缺失时静默跳过，无 warning 也无 debug 日志
- **D-08:** 多个 AGENTS.md 文件拼接时，每个片段前加 `# Source: <path>` 标题标注来源，片段间用双新行分隔。path 使用相对于运行上下文的可读路径
- **D-09:** profile 名称由调用方显式传入 `load_profile(name)`，不从 settings.json 读取。不修改 Settings 模型
- **D-10:** 同名 profile 先加载 global 目录的子文件，再用 project 目录的非空子文件覆盖。按字段独立合并
- **D-11:** profile 子文件缺失时跳过，字段留空。复用已有 `_read_file()` 逻辑
- **D-12:** 8 种模块类型使用硬编码映射表 `MODULE_DIRS: dict[str, str]`，module_name -> 子目录名
- **D-13:** 目录不存在时静默跳过，只返回存在的路径
- **D-14:** 测试时用 tmp_path 构建 mock 目录结构，通过 ConfigLoader 可选参数传入

### Claude's Discretion
- 具体的 `MODULE_DIRS` 映射表内容（与设计文档目录结构对应即可）
- `load_settings()` 内部文件读取的 error handling 策略（文件存在但 JSON 格式错误时 raise 还是 warning + 跳过）
- `load_agents_md()` 的返回类型和空结果处理
- `discover_paths()` 是否验证 module_name 在映射表中（未知名称 raise ValueError?）
- 测试文件组织和测试用例设计
- 新增文件的数量和命名（loader.py / discovery.py / instructions.py 等）

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | ConfigLoader 支持四级覆盖链加载 settings.json（env > local > project > global） | loader.py 中 load_settings() 实现，复用 merge_settings() + apply_env_vars() + Settings.model_validate() |
| CFG-04 | discover_paths(module_name) 返回优先级从低到高的目录路径列表 | loader.py 中 discover() 方法，使用 MODULE_DIRS 映射表和 Path.exists() 过滤 |
| CFG-05 | discover() 支持 8 种模块类型（skills/agents/commands/hooks/rules/profiles/memory/mcp） | MODULE_DIRS 硬编码映射表覆盖全部 8 种类型 |
| INS-01 | AGENTS.md 指令链按顺序加载（全局 -> 项目 -> local -> 父目录链 -> user.md） | instructions.py 中 load_agents_md() 实现，按 D-06/D-08 规则拼接 |
| INS-02 | 父目录链遍历从 CWD 到 root，遇到 .git/ 边界停止 | Path.parents 迭代 + .git/ 检测，按 D-05/D-06 实现 |
| INS-04 | Profile 加载 profiles/\<name\>/ 目录下 soul.md/agents.md/identity.md/tool_guidance.md | loader.py 中 load_profile() 方法，按 D-09/D-10/D-11 实现 |
| INS-05 | load_agents_md() 拼接全部指令返回完整字符串 | instructions.py 中 load_agents_md() 返回 str，空时返回空字符串 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ConfigLoader.load_settings() | Framework config/ | - | 纯配置加载，叶依赖，不涉及网络或运行时服务 |
| discover_paths() | Framework config/ | - | 路径发现逻辑，只依赖 pathlib |
| AGENTS.md 链加载 | Framework config/ | - | 文件读取和字符串拼接，纯 I/O |
| Profile 加载 | Framework config/ | Framework prompts/ (参考模式) | config/ 实现加载逻辑，参考 profiles.py 的 _read_file 模式 |
| 路径优先级排序 | Framework config/ | - | global < project 的排序规则是框架核心约定 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib (stdlib) | Python 3.11 | 路径操作、目录发现、文件存在检查 | 标准库，Phase 20 已使用，零新依赖 |
| json (stdlib) | Python 3.11 | 读取 settings.json | 标准库，与设计文档 JSON 格式一致 |
| os (stdlib) | Python 3.11 | os.environ 读取环境变量 | apply_env_vars() 已使用 |
| pydantic | 已安装 | Settings.model_validate() 验证 | Phase 20 已引入，版本已锁定 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| copy (stdlib) | Python 3.11 | deepcopy 防止输入变异 | apply_env_vars() 已使用 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 自定义 _read_file() | pathlib.read_text() 直接调用 | _read_file() 封装了 exists() 检查和 encoding=utf-8，复用更一致 [CITED: profiles.py] |
| os.path | pathlib | pathlib 面向对象更清晰，项目已有大量 pathlib 使用 [VERIFIED: codebase grep] |

**Installation:**
```bash
# 无新依赖需要安装
# 所有依赖均为 Python 标准库或 Phase 20 已安装的 pydantic
```

**Version verification:** 无新包。Python 3.11.14 已确认可用。Phase 20 的 pydantic 已安装且正常工作。

## Package Legitimacy Audit

> 本 phase 不安装任何新外部包。所有依赖为 Python 标准库（pathlib, json, os）和 Phase 20 已安装的 pydantic。无需运行 slopcheck。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (无新包) | - | - | - | - | - | - |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
ConfigLoader (loader.py)
  |
  |-- load_settings()
  |     |-- global_dir/settings.json ──read──> dict
  |     |-- project_dir/settings.json ──read──> dict
  |     |-- project_dir/settings.local.json ──read──> dict (skip if missing)
  |     |-- merge_settings(global, project, local) ──> merged dict
  |     |-- apply_env_vars(merged, os.environ) ──> final dict
  |     └── Settings.model_validate(final) ──> Settings
  |
  |-- discover(module_name)
  |     |-- MODULE_DIRS[module_name] ──> sub_dir_name
  |     |-- global_dir / sub_dir_name ──exists?──> Path
  |     |-- project_dir / sub_dir_name ──exists?──> Path
  |     └── return [existing_paths]  (low -> high priority)
  |
  |-- load_profile(name)
  |     |-- global_dir/profiles/<name>/ ──read──> dict of field->content
  |     |-- project_dir/profiles/<name>/ ──read──> dict of field->content
  |     └── merge: project non-empty fields override global fields
  |
  +-- load_agents_md()  (in instructions.py)
        |-- global_dir/AGENTS.md ──read──> str (skip if missing)
        |-- project_dir/AGENTS.md ──read──> str (skip if missing)
        |-- project_dir/AGENTS.local.md ──read──> str (skip if missing)
        |-- parent chain traversal:
        |     |-- find .git root via Path.parents
        |     |-- iterate from .git root down to project_dir
        |     └── each dir's AGENTS.md ──read──> str
        |-- global_dir/user.md ──read──> str (skip if missing)
        └── concatenate with "# Source: <path>" headers
```

### Recommended Project Structure
```
framework/agent_framework/config/
├── __init__.py       # barrel 导出 — 更新 __all__ 添加新符号
├── settings.py       # (Phase 20, 不修改) Settings 模型 + ENV_VAR_MAP + apply_env_vars
├── merge.py          # (Phase 20, 不修改) merge_settings() 合并函数
├── loader.py         # (Phase 21 新增) ConfigLoader 类 — load_settings, discover, load_profile
└── instructions.py   # (Phase 21 新增) load_agents_md() + 父目录链遍历辅助函数

framework/tests/
├── test_settings.py  # (Phase 20, 不修改)
├── test_merge.py     # (Phase 20, 不修改)
├── test_loader.py    # (Phase 21 新增) ConfigLoader + discover + load_profile 测试
└── test_instructions.py # (Phase 21 新增) load_agents_md + 父目录链测试
```

### Pattern 1: ConfigLoader 构造函数注入路径
**What:** 构造函数接受可选 Path 参数，默认值用 Path.home() / Path.cwd()，测试时注入 tmp_path
**When to use:** ConfigLoader 实例化
**Example:**
```python
# 来源: CONTEXT.md D-04
class ConfigLoader:
    def __init__(
        self,
        global_dir: Path = Path.home(),
        project_dir: Path = Path.cwd(),
    ) -> None:
        self._global_dir = global_dir / ".agent-framework"
        self._project_dir = project_dir / ".agent-framework"
```

### Pattern 2: 静默文件读取 + exists 检查
**What:** 文件不存在时返回空值（空字符串或跳过），不抛异常不打印日志
**When to use:** 所有配置文件和 AGENTS.md 文件读取
**Example:**
```python
# 来源: profiles.py _read_file() [VERIFIED: codebase read]
def _read_file(path: Path) -> str:
    """读文件内容，不存在返回空字符串。"""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
```

### Pattern 3: MODULE_DIRS 硬编码映射表
**What:** 模块类型名到子目录名的静态映射
**When to use:** discover() 方法查找目录路径
**Example:**
```python
# 来源: 设计文档第四节 + CONTEXT.md D-12
MODULE_DIRS: dict[str, str] = {
    "skills": "skills",
    "agents": "agents",
    "commands": "commands",
    "hooks": "hooks",
    "rules": "rules",
    "profiles": "profiles",
    "memory": "memory",
    "mcp": "mcp",
}
```

### Pattern 4: 父目录链遍历（.git 边界检测）
**What:** 从 CWD 向上找 .git 根目录，然后从根向下收集 AGENTS.md
**When to use:** load_agents_md() 中的父目录链部分
**Example:**
```python
# 来源: CONTEXT.md D-05, D-06
def _find_git_root(start: Path) -> Path | None:
    """从 start 向上遍历 parents，找到包含 .git/ 的目录。"""
    if (start / ".git").is_dir():
        return start
    for parent in start.parents:
        if (parent / ".git").is_dir():
            return parent
    return None

def _parent_agents_chain(project_dir: Path) -> list[Path]:
    """从 .git 根目录向下遍历到 project_dir，收集每层的 AGENTS.md。"""
    git_root = _find_git_root(project_dir)
    if git_root is None:
        return []
    # 从 git_root 的 parent 向下到 project_dir（不含 project_dir 本身）
    # 按 D-06: 越靠近 CWD 的文件后加载（高优先级）
    ...
```

### Anti-Patterns to Avoid
- **不要在 config/ 导入框架其他模块**: 叶依赖约束（INT-03）是架构硬约束，config/ 只能依赖 pydantic + 标准库。违反此约束会在 Phase 24 造成循环导入 [CITED: STATE.md Blockers/Concerns]
- **不要用 os.path 混用 pathlib**: 项目统一使用 pathlib，见 CONVENTIONS.md
- **不要对缺失文件做 logging.warning**: D-07 明确要求静默跳过，与 profiles.py 的 _read_file() 行为一致
- **不要修改 profiles.py 的 _read_file()**: 该函数属于 prompts/ 模块，config/ 不能导入它。在 instructions.py 或 loader.py 中重新实现同样的逻辑

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 配置合并 | 自写合并逻辑 | merge_settings() (Phase 20) | 已完整实现三种策略（标量覆盖/对象浅合并/数组并集），通过 170 行测试 |
| 环境变量注入 | 自写 env 解析 | apply_env_vars() (Phase 20) | 已实现 ENV_VAR_MAP 映射和嵌套路径注入 |
| Settings 验证 | 自写 schema 验证 | Settings.model_validate() | Pydantic 验证自带类型检查和默认值填充 |

**Key insight:** Phase 21 的核心工作量不在合并/验证逻辑（Phase 20 已完成），而在文件读取编排和路径发现。

## Common Pitfalls

### Pitfall 1: 父目录链方向错误
**What goes wrong:** 从 CWD 向上遍历 vs 从 .git 根向下遍历搞混
**Why it happens:** 两个方向在简单情况下结果一样（只有一层父目录时），容易忽视方向差异
**How to avoid:** D-06 明确要求"从 .git 根目录向下遍历到 CWD"。需要先找到 .git 根，再从根向 CWD 方向遍历。测试用多层嵌套目录验证
**Warning signs:** 单层目录测试通过但多层失败

### Pitfall 2: settings.local.json 路径拼接
**What goes wrong:** local.json 和 project settings.json 不在同目录
**Why it happens:** 混淆 global_dir 和 project_dir 的子路径
**How to avoid:** D-03 明确 local.json 与 project settings.json 同目录（都在 `.agent-framework/` 下）
**Warning signs:** 测试中 local 覆盖不生效

### Pitfall 3: Path.cwd() 在测试中的行为
**What goes wrong:** 测试中 Path.cwd() 返回实际工作目录而非 tmp_path
**Why it happens:** pytest 的 tmp_path fixture 不改变 cwd
**How to avoid:** D-14 明确通过构造函数参数注入 tmp_path，不依赖 Path.cwd()
**Warning signs:** 测试在 CI 中失败（CI 的 cwd 不同）

### Pitfall 4: 叶依赖违反
**What goes wrong:** 在 loader.py 中 import agent_framework.prompts.profiles
**Why it happens:** 想复用 _read_file() 函数
**How to avoid:** 在 config/ 内部重新实现 _read_file()（3 行代码），不导入 prompts 模块
**Warning signs:** TestLeafDependency 测试失败

### Pitfall 5: JSON 解析错误的处理策略
**What goes wrong:** settings.json 存在但格式错误时，行为未定义
**Why it happens:** D-07 只覆盖"文件缺失"，未覆盖"文件损坏"
**How to avoid:** 这是 Claude's Discretion 区域。建议：JSON 解析错误时 raise ValueError，因为静默跳过损坏的配置会导致难以调试的行为差异
**Warning signs:** 无明确的错误反馈，用户不理解为什么设置没生效

### Pitfall 6: Profile 字段合并的"非空覆盖"
**What goes wrong:** project 的空字符串覆盖 global 的有效内容
**Why it happens:** D-10 说"非空覆盖"，但实现时误用简单赋值
**How to avoid:** 合并逻辑：仅当 project 字段非空时才覆盖 global 字段
**Warning signs:** profile 加载后某些字段意外为空

## Code Examples

### ConfigLoader.load_settings() 完整流程
```python
# 来源: CONTEXT.md specifics + Phase 20 settings.py/merge.py [VERIFIED: codebase read]
import json
from pathlib import Path
from agent_framework.config.merge import merge_settings
from agent_framework.config.settings import Settings, apply_env_vars

class ConfigLoader:
    def __init__(
        self,
        global_dir: Path = Path.home(),
        project_dir: Path = Path.cwd(),
    ) -> None:
        self._global_dir = global_dir / ".agent-framework"
        self._project_dir = project_dir / ".agent-framework"

    def load_settings(self) -> Settings:
        """四级覆盖链加载 settings.json，返回 Settings 实例。"""
        global_cfg = self._read_json(self._global_dir / "settings.json")
        project_cfg = self._read_json(self._project_dir / "settings.json")
        local_cfg = self._read_json(self._project_dir / "settings.local.json")
        merged = merge_settings(global_cfg, project_cfg, local_cfg)
        import os
        final = apply_env_vars(merged, dict(os.environ))
        return Settings.model_validate(final)

    def _read_json(self, path: Path) -> dict:
        """读取 JSON 文件，不存在返回空 dict。"""
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
```

### discover() 方法
```python
# 来源: CONTEXT.md D-02, D-12, D-13 + 设计文档第四节
MODULE_DIRS: dict[str, str] = {
    "skills": "skills",
    "agents": "agents",
    "commands": "commands",
    "hooks": "hooks",
    "rules": "rules",
    "profiles": "profiles",
    "memory": "memory",
    "mcp": "mcp",
}

class ConfigLoader:
    def discover(self, module_name: str) -> list[Path]:
        """返回优先级从低到高的模块目录路径列表。"""
        sub_dir = MODULE_DIRS.get(module_name)
        if sub_dir is None:
            raise ValueError(f"未知模块类型: {module_name}")
        paths: list[Path] = []
        for base in (self._global_dir, self._project_dir):
            module_path = base / sub_dir
            if module_path.is_dir():
                paths.append(module_path)
        return paths
```

### load_agents_md() 父目录链拼接
```python
# 来源: CONTEXT.md D-05, D-06, D-07, D-08
def _find_git_root(start: Path) -> Path | None:
    """从 start 向上查找包含 .git/ 的目录。"""
    if (start / ".git").is_dir():
        return start
    for parent in start.parents:
        if (parent / ".git").is_dir():
            return parent
    return None

def _read_agents_file(path: Path) -> str:
    """读取 AGENTS.md 文件，不存在返回空字符串。"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

class ConfigLoader:
    def load_agents_md(self) -> str:
        """拼接完整的 AGENTS.md 指令链。"""
        parts: list[str] = []

        # 1. global AGENTS.md
        # 2. project AGENTS.md
        # 3. project AGENTS.local.md
        # 4. 父目录链（.git root -> project_dir）
        # 5. global user.md

        sources = [
            (self._global_dir / "AGENTS.md", "~/.agent-framework/AGENTS.md"),
            (self._project_dir / "AGENTS.md", ".agent-framework/AGENTS.md"),
            (self._project_dir / "AGENTS.local.md", ".agent-framework/AGENTS.local.md"),
        ]

        # 父目录链
        project_root = self._project_dir.parent  # .agent-framework 的父目录
        git_root = _find_git_root(project_root)
        if git_root is not None and git_root != project_root:
            # 从 git_root 向下到 project_root 的中间目录
            chain_dirs = []
            current = project_root
            while current != git_root and current != current.parent:
                chain_dirs.append(current)
                current = current.parent
            # 反转：从 git_root 附近到 project_root 附近（低 -> 高优先级）
            for d in reversed(chain_dirs):
                rel = d.relative_to(project_root)
                sources.append((d / "AGENTS.md", f"{rel}/AGENTS.md"))

        # user.md
        sources.append(
            (self._global_dir / "user.md", "~/.agent-framework/user.md")
        )

        for path, label in sources:
            content = _read_agents_file(path)
            if content.strip():
                parts.append(f"# Source: {label}\n{content}")

        return "\n\n".join(parts)
```

### load_profile() 字段合并
```python
# 来源: CONTEXT.md D-09, D-10, D-11
PROFILE_FILES = ["soul.md", "agents.md", "identity.md", "tool_guidance.md"]

class ConfigLoader:
    def load_profile(self, name: str) -> dict[str, str]:
        """加载并合并指定 profile 的字段。返回 {field_name: content}。"""
        result: dict[str, str] = {}

        # 先加载 global
        global_profile_dir = self._global_dir / "profiles" / name
        for filename in PROFILE_FILES:
            field = filename.replace(".md", "")
            content = _read_agents_file(global_profile_dir / filename).strip()
            if content:
                result[field] = content

        # 再用 project 的非空字段覆盖
        project_profile_dir = self._project_dir / "profiles" / name
        for filename in PROFILE_FILES:
            field = filename.replace(".md", "")
            content = _read_agents_file(project_profile_dir / filename).strip()
            if content:
                result[field] = content

        return result
```

### barrel __init__.py 更新模式
```python
# 来源: Phase 20 __init__.py 模式 [VERIFIED: codebase read]
"""全局运行时配置模块 — barrel 导出。"""

from __future__ import annotations

from agent_framework.config.merge import merge_settings
from agent_framework.config.settings import (
    ENV_VAR_MAP,
    LlmConfig,
    LoggingConfig,
    PermissionsConfig,
    ServerConfig,
    Settings,
    apply_env_vars,
)

# Phase 21 新增导出
from agent_framework.config.loader import ConfigLoader
from agent_framework.config.instructions import load_agents_md

__all__ = [
    # Phase 20
    "ENV_VAR_MAP",
    "LlmConfig",
    "LoggingConfig",
    "PermissionsConfig",
    "ServerConfig",
    "Settings",
    "apply_env_vars",
    "merge_settings",
    # Phase 21
    "ConfigLoader",
    "load_agents_md",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 分散的 BaseSettings (backend) | 统一 ConfigLoader 入口 | v0.0.6 Phase 21 | 所有模块通过同一个 loader 获取配置 |
| 硬编码目录路径 | discover() 路径发现 | v0.0.6 Phase 21 | 模块自动发现全局和项目级资源 |
| 单目录 profile 加载 | 双路径合并 profile 加载 | v0.0.6 Phase 21 | 支持 global + project 级别 profile 覆盖 |

**Deprecated/outdated:**
- backend/app/config/__init__.py 的 BaseSettings: Phase 24 将替换为从 ConfigLoader 获取默认值
- 直接调用 Path.home() / ".agent-framework" 硬编码: Phase 21 后统一通过 ConfigLoader

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 父目录链遍历中，project_dir 指的是 `.agent-framework/` 的父目录（即 CWD 或 ConfigLoader 传入的 project_dir 参数的父级） | Architecture Patterns, load_agents_md | 如果 project_dir 应该是 `.agent-framework/` 本身，链的起点会差一层 |
| A2 | load_profile() 返回 dict[str, str] 而非 AgentProfile 对象 | Code Examples | 如果应返回 AgentProfile，需要导入 profiles.py（违反叶依赖） |
| A3 | instructions.py 中的 load_agents_md 作为独立函数而非 ConfigLoader 方法 | Architecture Patterns | 如果应该是 ConfigLoader 方法，文件组织需调整 |
| A4 | Path.parents 遍历在 .git 位于 CWD 时也能正确工作 | Code Examples | 已验证：CWD 就是 .git 所在目录时，_find_git_root 返回 CWD，父目录链为空 |

## Open Questions

1. **load_profile() 返回类型**
   - What we know: D-09 说名称由调用方传入，D-10 说按字段独立合并
   - What's unclear: 返回 dict[str, str] 还是某种 Profile 对象
   - Recommendation: 返回 dict[str, str]，因为 config/ 不能导入 profiles.AgentProfile（叶依赖）。Phase 23 的适配器负责转换为 AgentProfile

2. **instructions.py 独立函数 vs ConfigLoader 方法**
   - What we know: load_agents_md 需要 global_dir 和 project_dir
   - What's unclear: 是 ConfigLoader.load_agents_md() 还是独立函数接受 loader 参数
   - Recommendation: 作为 ConfigLoader 的方法最自然——它需要 global_dir 和 project_dir，正好是构造函数已有的状态

3. **_read_file() 复制 vs 导入**
   - What we know: profiles.py 有 _read_file()，config/ 不能导入它
   - What's unclear: 是否值得提取为共享工具函数
   - Recommendation: 在 config/ 内部重新实现（仅 3 行），保持叶依赖。函数极简，不值得为此引入跨模块依赖

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | 所有代码 | ✓ | 3.11.14 | - |
| pydantic | Settings.model_validate | ✓ | Phase 20 已安装 | - |
| pytest | 测试运行 | ✓ | 已安装 | - |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | framework/pyproject.toml (pytest section) |
| Quick run command | `cd framework && pytest tests/test_loader.py tests/test_instructions.py -v` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | load_settings 四级覆盖链 | unit | `pytest tests/test_loader.py::TestLoadSettings -v` | Wave 0 |
| CFG-04 | discover_paths 返回有序路径 | unit | `pytest tests/test_loader.py::TestDiscover -v` | Wave 0 |
| CFG-05 | 8 种模块类型发现 | unit | `pytest tests/test_loader.py::TestDiscover::test_all_eight_module_types -v` | Wave 0 |
| INS-01 | AGENTS.md 链顺序加载 | unit | `pytest tests/test_instructions.py::TestLoadAgentsMd -v` | Wave 0 |
| INS-02 | 父目录链 .git 边界 | unit | `pytest tests/test_instructions.py::TestParentChain -v` | Wave 0 |
| INS-04 | Profile 双路径合并 | unit | `pytest tests/test_loader.py::TestLoadProfile -v` | Wave 0 |
| INS-05 | load_agents_md 完整拼接 | unit | `pytest tests/test_instructions.py::TestLoadAgentsMd -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/test_loader.py tests/test_instructions.py -v`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** Full suite green (1040 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `framework/tests/test_loader.py` — covers CFG-01, CFG-04, CFG-05, INS-04
- [ ] `framework/tests/test_instructions.py` — covers INS-01, INS-02, INS-05
- [ ] `framework/agent_framework/config/loader.py` — ConfigLoader 实现
- [ ] `framework/agent_framework/config/instructions.py` — AGENTS.md 链加载

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | - |
| V3 Session Management | no | - |
| V4 Access Control | no | - |
| V5 Input Validation | yes | JSON 解析错误处理，路径验证 |
| V6 Cryptography | no | - |

### Known Threat Patterns for Config Loading Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal | Tampering | ConfigLoader 的 base_dir 由构造函数注入，discover() 只在 base_dir 子目录内操作 |
| JSON injection | Tampering | json.loads() 自然防护，不 eval；Pydantic Settings.model_validate() 做类型校验 |
| Info disclosure | Information Disclosure | settings.local.json 包含敏感信息（API key），由 .gitignore 保护；框架层不处理 .gitignore |

## Sources

### Primary (HIGH confidence)
- `docs/plans/2026-06-11-config-path-mechanism-design.md` — 完整设计文档：目录结构、优先级、合并规则
- `framework/agent_framework/config/settings.py` — Phase 20 Settings 模型（已读源码）
- `framework/agent_framework/config/merge.py` — Phase 20 合并引擎（已读源码）
- `framework/agent_framework/config/__init__.py` — barrel 导出模式（已读源码）
- `framework/agent_framework/prompts/profiles.py` — _read_file() 和 from_directory() 模式（已读源码）
- `.planning/codebase/CONVENTIONS.md` — 编码规范（已读）
- `.planning/codebase/ARCHITECTURE.md` — 架构约束（已读）

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — 需求定义（CFG-01, CFG-04, CFG-05, INS-01~05）
- `.planning/ROADMAP.md` — Phase 21 成功标准和 plan 拆分建议
- `framework/agent_framework/prompts/assembler.py` — PromptAssembler 集成参考（已读源码）
- `framework/agent_framework/agents/config.py` — AgentConfig 加载模式参考（已读源码）
- `framework/agent_framework/skills/registry.py` — 多目录扫描模式参考（已读源码）

### Tertiary (LOW confidence)
- None — 所有核心代码已直接读源码验证

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 无新依赖，纯标准库 + Phase 20 已验证包
- Architecture: HIGH - 设计文档详尽，CONTEXT.md 有 14 个锁定决策，Phase 20 代码已读
- Pitfalls: HIGH - 6 个 pitfalls 全部来自已读代码和设计文档的交叉分析
- Code examples: HIGH - 基于 Phase 20 已验证代码模式 + CONTEXT.md 决策

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (30 days — 稳定的标准库 + 项目内部设计)
