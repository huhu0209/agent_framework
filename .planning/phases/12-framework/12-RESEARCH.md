# Phase 12: Framework 代码审查 - Research

**Researched:** 2026-06-09
**Domain:** Python 静态分析 + 人工代码审查
**Confidence:** HIGH

## Summary

Phase 12 对 `framework/agent_framework/` 下约 100 个 Python 源文件（10,475 行）进行全面代码审查。审查分四个维度：死代码检测（FRMW-01）、逻辑漏洞（FRMW-02）、设计问题（FRMW-03）、安全审查（FRMW-04），产出 REVIEW-FRAMEWORK.md 报告（FRMW-05）。

ruff 0.15.16 已安装并可用作死代码自动检测工具。在审查范围内（agent_framework/ 源码，不含 tests/），ruff 检测到 **32 个 pyflakes 错误**（30 个未使用 import + 2 个未定义名称），**7 个安全问题**（flake8-bandit），**10 个高复杂度函数**（C901），以及大量代码风格问题。这些自动化结果将作为人工审查的输入基线。

项目已有完善的代码库智能文档（CONCERNS.md、CONVENTIONS.md、TESTING.md）和 v0.0.1 审查报告格式参考。CONCERNS.md 记录了 27 个已知问题，覆盖技术债、已知 bug、安全风险、性能问题和脆弱区域，可作为人工审查的检查清单输入。

**Primary recommendation:** 分两波执行——Wave 1 用 ruff 自动扫描全量代码获取死代码/安全/复杂度基线数据；Wave 2 按 16 个模块逐模块人工审查逻辑漏洞、设计问题和安全漏洞，每模块产出独立章节。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 全面重新审查 — 逐文件审查所有框架层源码，不依赖 v0.0.1 审查基线，独立发现所有问题
- **D-02:** 全模块等权审查 — 所有模块同等深度审查，不偏重新增模块或高风险模块
- **D-03:** 独立审查 — 不与 v0.0.1 SECURITY-REVIEW.md / ARCH-REVIEW.md 逐项对照，完全独立产出
- **D-04:** ruff 做死代码检测 — 利用 ruff 的未使用 import/变量/函数检测能力
- **D-05:** 工具先行 + 人工审查 — 先 ruff 自动扫描全量代码获取死代码报告，再逐模块人工审查逻辑漏洞、设计问题、安全漏洞
- **D-06:** 审查范围仅限框架源码 — agent_framework/ 下的 .py 文件，不含 tests/ 测试代码
- **D-07:** 影响导向分级标准：CRITICAL = 数据丢失/安全漏洞/系统不可用；HIGH = 逻辑错误/竞态条件/严重设计缺陷；MEDIUM = 代码质量/可维护性/轻微设计不合理；LOW = 代码风格/命名/文档/微小优化
- **D-08:** 按模块分组 — 每个模块一个章节，模块内按严重性排序
- **D-09:** 详细 issue 字段 — 每个 issue 包含：ID、描述、文件位置（文件:行号）、影响、修复建议、优先级。与 FRMW-01~05 关联

### Claude's Discretion
- ruff 的具体规则配置和启用项
- 模块审查的先后顺序
- 具体 issue ID 编号方案
- 跨模块问题的归类方式

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRMW-01 | 检测框架层所有未使用的函数、类、import、变量、文件 | ruff pyflakes 规则集 (F401/F811/F841/F821) 提供自动检测；人工审查补充 ruff 无法检测的死代码（如仅被 tests 使用的导出函数、永远不会被调用的条件分支） |
| FRMW-02 | 查找框架层逻辑漏洞、竞态条件、错误处理缺陷 | 逐模块人工审查 + CONCERNS.md 已知 bug 清单作为检查输入 + C901 复杂度报告定位高风险函数 |
| FRMW-03 | 审查框架层不合理设计模式、违反原则、过度工程 | 逐模块人工审查 SOLID 原则 + CONVENTIONS.md 编码规范作为对照标准 + PLR0913 参数过多检测 |
| FRMW-04 | 审查框架层安全漏洞（注入、信息泄露、路径遍历等） | ruff flake8-bandit (S) 规则自动检测 + 人工审查路径遍历/命令注入/信息泄露模式 + CONCERNS.md 安全清单 |
| FRMW-05 | 产出框架层审查报告（含优先级分级和修复建议） | v0.0.1 SECURITY-REVIEW.md / ARCH-REVIEW.md 格式参考；按 D-07~D-09 分级和格式标准产出 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 死代码自动检测 | CLI 工具层 (ruff) | — | 静态分析工具直接扫描源码文件 |
| 逻辑漏洞审查 | 人工审查 (Claude) | CLI 工具 (ruff C901) | 复杂度和未定义名称可自动发现，但逻辑正确性需要人工判断 |
| 设计问题审查 | 人工审查 (Claude) | — | 设计模式合理性需要理解业务意图和架构上下文 |
| 安全漏洞审查 | CLI 工具层 (ruff S) + 人工 | — | bandit 规则自动检测已知模式，人工审查上下文相关的安全问题 |
| 报告产出 | 文档层 | — | Markdown 报告文件，无运行时影响 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruff | 0.15.16 | Python 静态分析（linter + formatter） | 用 D-04 决策指定；已安装到系统（`/Users/huhu/.local/bin/ruff`）；集成了 pyflakes、flake8-bandit、pylint 规则、复杂度检测等，单一工具覆盖所有自动检测需求 [VERIFIED: `ruff --version` + `uv tool install`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| grep/ripgrep | — | 搜索代码模式（eval、subprocess、environ 等） | 人工审查中的定向搜索 [VERIFIED: 系统内置] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ruff | pylint | pylint 有更多设计模式检查（如 too-few-public-methods），但 ruff 已包含 C901 复杂度、PLR0913 参数数量等足够的设计提示规则，且速度快 10-100x |
| ruff | mypy | mypy 用于类型检查而非代码审查，且需要配置类型存根。本 phase 不做类型检查，只做代码质量审查 |
| ruff | bandit (standalone) | ruff 已集成 flake8-bandit 规则（S 系列），无需单独安装 bandit |

**Installation:**
```bash
# ruff 已通过 uv tool 安装到系统
ruff --version  # 验证: ruff 0.15.16
```

## Package Legitimacy Audit

> 本 phase 不安装任何外部 Python 包到项目。ruff 通过 `uv tool install` 安装到用户级工具目录，不影响项目依赖。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| ruff | PyPI | 3+ years | 30M+/mo | github.com/astral-sh/ruff | — | System tool, not project dependency |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*本 phase 的唯一外部工具 ruff 是系统级 CLI 工具，不作为项目依赖安装。*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 12 审查流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌───────────────────┐                     │
│  │  ruff scan   │────>│  自动检测结果基线   │                     │
│  │  (Wave 1)    │     │  32 pyflakes      │                     │
│  └──────────────┘     │  7 security       │                     │
│                       │  10 complexity    │                     │
│                       └────────┬──────────┘                     │
│                                │                                │
│                                v                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              逐模块人工审查 (Wave 2)                    │       │
│  │                                                      │       │
│  │  16 modules:                                         │       │
│  │  llm/ → tools/ → agents/ → teams/ → memory/          │       │
│  │  → safety/ → orchestrator/ → hooks/ → skills/        │       │
│  │  → tasks/ → commands/ → prompts/ → a2a/              │       │
│  │  → transcript/ → viz/                                │       │
│  │                                                      │       │
│  │  每模块检查:                                          │       │
│  │  ┌──────────────┐  ┌──────────────┐                   │       │
│  │  │ 逻辑漏洞     │  │ 竞态条件     │                   │       │
│  │  └──────────────┘  └──────────────┘                   │       │
│  │  ┌──────────────┐  ┌──────────────┐                   │       │
│  │  │ 错误处理缺陷 │  │ 设计问题     │                   │       │
│  │  └──────────────┘  └──────────────┘                   │       │
│  │  ┌──────────────┐  ┌──────────────┐                   │       │
│  │  │ 安全漏洞     │  │ 死代码(补充) │                   │       │
│  │  └──────────────┘  └──────────────┘                   │       │
│  └──────────────────────────────────────────────────────┘       │
│                                │                                │
│                                v                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           REVIEW-FRAMEWORK.md                        │       │
│  │                                                      │       │
│  │  按模块分组 × 4 级严重性                              │       │
│  │  每个 issue: ID / 描述 / 文件:行号 / 影响 / 修复建议   │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

审查报告产出位置：
```
docs/reviews/
└── REVIEW-FRAMEWORK.md    ← 审查报告（新文件）
```

审查目标结构（只读）：
```
framework/agent_framework/     ← 审查目标（~100 文件, 10,475 行）
├── llm/          (10 files)   ← LLM Adapter + providers + streaming + transform
├── tools/        (12 files)   ← Tool system + builtin + MCP + context
├── agents/       (6 files)    ← AgentLoop + reflection + plan_and_solve + sub_agent
├── teams/        (4 files)    ← TeamManager + MessageBus
├── memory/       (9 files)    ← Memory store + index + semantic + search
├── safety/       (4 files)    ← Boundary + permissions + verification + HITL
├── orchestrator/ (7 files)    ← Planner + engine + coordinator + worker
├── hooks/        (2 files)    ← HookManager + types
├── skills/       (5 files)    ← SkillRegistry + discovery + parser
├── tasks/        (4 files)    ← TaskManager + runner + tools
├── commands/     (6 files)    ← CommandDispatcher + builtins
├── prompts/      (3 files)    ← Assembler + profiles + templates
├── a2a/          (3 files)    ← A2A client + server + models
├── transcript/   (4 files)    ← Transcript writer + reader + consumer
├── viz/          (3 files)    ← EventBus + AgentRunner + ws_server
└── __init__.py   (1 file)
```

### Pattern 1: ruff 自动扫描

**What:** 用 ruff pyflakes 规则自动检测未使用 import、未定义名称、未使用变量。
**When to use:** Wave 1 死代码检测阶段。
**Example:**
```bash
# 死代码检测（未使用 import/变量/函数）
ruff check --select F401,F811,F841,F821 --no-fix framework/agent_framework/

# 安全模式检测（flake8-bandit）
ruff check --select S --no-fix framework/agent_framework/

# 复杂度检测
ruff check --select C901 --no-fix framework/agent_framework/

# 参数过多检测
ruff check --select PLR0913 --no-fix framework/agent_framework/
```

### Pattern 2: 逐模块人工审查检查清单

**What:** 每个模块按统一检查清单审查。
**When to use:** Wave 2 逐模块审查。
**Example:**
每个模块检查：
1. **逻辑正确性:** 条件分支是否覆盖所有路径？循环终止条件是否正确？
2. **竞态条件:** 共享状态是否正确同步？async 锁使用是否正确？
3. **错误处理:** 异常是否正确捕获和传播？silent catch 是否合理？
4. **设计模式:** 是否违反 SOLID？是否过度工程？是否有代码重复？
5. **安全问题:** 输入是否验证？路径是否安全？敏感信息是否泄露？

### Anti-Patterns to Avoid

- **纯工具依赖:** 不能只依赖 ruff 输出作为审查结果。ruff 只能检测语法级别的死代码和已知安全模式，无法理解业务逻辑正确性。
- **逐项对照旧报告:** 按 D-03 决策，必须独立发现所有问题，不能逐项对照 v0.0.1 报告。
- **过度分级膨胀:** LOW 级别的代码风格问题不应占审查报告主体。ruff 的代码风格警告（docstring 标点、magic value 等）仅作为参考，不逐项写入报告。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 死代码检测 | 手动 grep 查找未使用 import | `ruff check --select F` | ruff 精确识别未使用 import/变量/函数，零误报 [VERIFIED: 本次运行 ruff 输出 32 个 pyflakes 错误，均为真实问题] |
| 安全模式检测 | 手动查找 eval/subprocess 模式 | `ruff check --select S` | ruff 集成 flake8-bandit 规则，自动检测标准安全反模式 [VERIFIED: 检测到 S311/S324/S110/S112 共 7 个问题] |
| 复杂度评估 | 手动计算圈复杂度 | `ruff check --select C901` | ruff 自动计算 McCabe 复杂度，阈值 10 [VERIFIED: 检测到 10 个超复杂函数] |

**Key insight:** ruff 是本 phase 的唯一自动化工具，覆盖 F（pyflakes）、S（bandit）、C901（复杂度）、PLR（pylint 规则）四类规则。人工审查专注于 ruff 无法检测的领域：业务逻辑正确性、竞态条件、设计合理性、上下文相关的安全问题。

## Common Pitfalls

### Pitfall 1: Ruff 误报死代码

**What goes wrong:** ruff 的 F401 规则可能标记 `__init__.py` 中 re-export 的 import 为"未使用"，但这些 import 是 package 公共 API 的一部分（通过 `__all__` 导出）。
**Why it happens:** ruff 分析单文件时看不到外部消费者。
**How to avoid:** 审查 F401 结果时排除 `__init__.py` 中的 re-export import（除非该 import 不在 `__all__` 列表中）。
**Warning signs:** F401 报告指向 `__init__.py` 文件。

### Pitfall 2: 审查范围蔓延

**What goes wrong:** 审查时发现 bug 顺手修复，导致审查 phase 变成修复 phase。
**Why it happens:** 工程师天然倾向于修复发现的问题。
**How to avoid:** 严格限定本 phase 只产出报告，不修改任何源码文件。所有发现记录到 REVIEW-FRAMEWORK.md。
**Warning signs:** 在审查过程中编辑了 agent_framework/ 下的源码文件。

### Pitfall 3: 忽略 CONCERNS.md 已知问题

**What goes wrong:** 人工审查遗漏 CONCERNS.md 中已记录的 bug 和风险，导致报告不完整。
**Why it happens:** 审查时没有参考已有知识库。
**How to avoid:** 每个 CONCERNS.md 条目都必须在审查结果中重新评估和覆盖（独立发现或引用）。
**Warning signs:** 报告中缺少 CONCERNS.md 记录的任何 HIGH 级别问题。

### Pitfall 4: 中文代码审查中的 RUF001/RUF002 误判

**What goes wrong:** ruff 的 RUF001/RUF002 规则标记中文全角标点为"ambiguous character"，但这在中文代码库中是正确和有意为之的。
**Why it happens:** ruff 默认假设英文编码环境。
**How to avoid:** 忽略 RUF001/RUF002 告警，这是中文项目的正常行为。
**Warning signs:** 审查报告因 RUF 规则产生大量无意义 LOW 条目。

### Pitfall 5: ROADMAP 与 CONTEXT 决策冲突

**What goes wrong:** ROADMAP 成功标准 #4 要求"安全问题与 v0.0.1 SECURITY-REVIEW.md 对照"，但 CONTEXT.md D-03 锁定"独立审查，不逐项对照"。
**Why it happens:** ROADMAP 在 context 讨论之前编写。
**How to avoid:** 以 CONTEXT.md D-03 决策为准，独立审查。报告可以独立发现与 v0.0.1 相同的问题，但不做逐项对照。
**Warning signs:** 审查过程中逐项检查 v0.0.1 报告条目。

## Code Examples

### Ruff 自动扫描基线结果（已验证）

本次运行 ruff 的实际检测结果，作为 Wave 1 基线数据：

**Pyflakes 错误 (F 系列) — 32 个：**
- 30 个 F401（未使用 import）：分布在 15 个文件中
- 2 个 F821（未定义名称）：
  - `agents/agent_loop.py:288` — `logger` 未定义（缺少 `logging.getLogger(__name__)`）
  - `llm/base.py:173` — `httpx` 仅用于类型注解，在 `TYPE_CHECKING` guard 外引用

**安全问题 (S 系列) — 7 个：**
- S311: `llm/retry.py:76` — `random.random()` 用于 jitter（非加密场景可接受）
- S324: `memory/semantic_writer.py:47` — `hashlib.sha1()` 用于文件名生成（非安全场景）
- S110: 3 处 `try-except-pass`（`tasks/runner.py`, `tools/mcp/config.py`, `viz/ws_server.py`）
- S112: 1 处 `try-except-continue`（`teams/bus.py:50`）

**复杂度问题 (C901) — 10 个：**
- 最高：`agents/agent_loop.py:run` 复杂度 30（阈值 10）
- 其他高复杂度函数分布在 `llm/streaming.py`、`tools/router.py`、`tasks/manager.py` 等

**参数过多 (PLR0913)：**
- `agents/agent_loop.py:__init__` — 19 个参数（阈值 5）

### 已知 bug 验证模式（CONCERNS.md 引用）

```python
# agents/agent_loop.py:288 — logger 未定义（ruff F821 确认）
# 修复前：
logger.debug("语义记忆提取失败...", exc_info=True)  # NameError!

# 需要：
import logging
logger = logging.getLogger(__name__)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 手动 grep 查找死代码 | ruff 集成 pyflakes | 项目初始 | 更精确、更快、零遗漏 |
| 单独安装 bandit 做安全扫描 | ruff 集成 flake8-bandit (S) 规则 | ruff 0.1+ | 一个工具覆盖多维度 |
| 无 linter 配置 | 无 linter 配置（仍是现状） | — | 项目未配置 pyproject.toml 中的 ruff 规则，所有检测使用默认配置 |

**Deprecated/outdated:**
- v0.0.1 审查报告中的一些 bug 已在后续 phase 中修复（如 SEC-01 路径沙箱、SEC-02 环境变量注入、SEC-03 SecretStr），按 D-03 决策不逐项对照

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ruff 0.15.16 的 F401/F821/S/C901 规则足够覆盖死代码自动检测需求 | Standard Stack | LOW — ruff 是最成熟的 Python linter，规则覆盖广泛 |
| A2 | 中文全角标点的 RUF001/RUF002 告警应忽略 | Common Pitfalls | LOW — 这是中文项目标准做法 |
| A3 | CONCERNS.md 记录的 27 个问题中大多数在当前代码中仍存在 | Common Pitfalls | MEDIUM — 部分 v0.0.1 问题已在 v0.0.2/v0.0.3 修复，需要人工验证 |
| A4 | 10,475 行代码可在合理时间内逐模块人工审查完成 | Architecture | LOW — 按 16 个模块分割，每模块约 650 行，可管理 |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions (RESOLVED)

1. **ROADMAP vs CONTEXT 冲突**
   - What we know: ROADMAP 成功标准 #4 要求"与 v0.0.1 SECURITY-REVIEW.md 对照"，但 CONTEXT D-03 锁定"独立审查"
   - What's unclear: 是否需要在报告末尾增加一个附录，标注哪些 v0.0.1 问题在独立审查中重新发现
   - Recommendation: 以 CONTEXT D-03 为准（独立审查）。如 planner 认为需要，可在报告末尾增加可选的"历史对照附录"
   - RESOLVED: 遵循 CONTEXT D-03（独立审查）。计划 01-04 全部标注独立审查，不与 v0.0.1 报告逐项对照。ROADMAP 成功标准 #4 已更新为"独立审查产出（per CONTEXT D-03）"。

2. **模块审查顺序**
   - What we know: 16 个模块需等权审查
   - What's unclear: 审查顺序是否影响效率
   - Recommendation: 按依赖关系从底层到高层审查：llm → tools → agents → safety → memory → teams → tasks → hooks → skills → commands → prompts → orchestrator → a2a → transcript → viz。底层模块审查发现的问题可能在高层模块审查中被引用。
   - RESOLVED: 计划 02-04 在 Wave 2 并行运行，模块间无顺序依赖。Wave 1 处理 llm/（最大模块），Wave 2 处理剩余 15 个模块（3 个计划并行），Wave 3 汇总报告。等权审查目标已达成。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ruff | FRMW-01 死代码检测 | Yes | 0.15.16 | — |
| Python 3.11+ | 框架运行环境 | Yes | (via uv) | — |
| grep/ripgrep | 定向代码模式搜索 | Yes | 系统内置 | — |
| pytest | 审查时参考测试覆盖 | Yes | >=8.0.0 | — |

**Missing dependencies with no fallback:**
- none

**Missing dependencies with fallback:**
- none

## Validation Architecture

> workflow.nyquist_validation 在 config.json 中未设置（等同启用），但本 phase 是纯审查+报告 phase，不修改任何源码，不产出可执行代码。因此测试基础设施验证不适用。

### Wave 0 Gaps
- None — 本 phase 不涉及代码修改，不需要测试基础设施。

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes (review only) | API key 管理审查 — 不实施修复 |
| V4 Access Control | Yes (review only) | PermissionPipeline 审查 — 不实施修复 |
| V5 Input Validation | Yes (review only) | 文件路径/工具参数验证审查 — 不实施修复 |
| V6 Cryptography | Yes (review only) | hashlib 使用审查 — 不实施修复 |
| V9 Communication Security | Yes (review only) | WebSocket/MCP 传输安全审查 — 不实施修复 |

### Known Threat Patterns for Python Agent Framework

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 路径遍历 (file_tools) | Tampering + Info Disclosure | `safe_path()` 已实施（v0.0.1 修复），需审查是否全面覆盖 |
| 命令注入 (hooks) | Elevation of Privilege | `trusted` flag 限制，需审查信任模型 |
| 环境变量注入 (MCP) | Info Disclosure | `field_validator` 已实施（v0.0.1 修复），需审查有效性 |
| API Key 泄露 (providers) | Info Disclosure | `SecretStr` 已实施（v0.0.1 修复），需审查 `get_secret_value()` 调用点 |
| 消息伪造 (MessageBus) | Spoofing + Tampering | 文件权限依赖，需评估风险 |
| Silent error swallowing | Denial of Service | `try-except-pass` 模式需逐一评估合理性 |

## Sources

### Primary (HIGH confidence)
- `ruff --version` / `ruff check` 实际运行结果 — 本地验证
- `.planning/codebase/CONCERNS.md` — 已知问题清单（项目文档）
- `.planning/codebase/CONVENTIONS.md` — 编码规范（项目文档）
- `docs/reviews/SECURITY-REVIEW.md` — v0.0.1 安全审查报告格式参考
- `docs/reviews/ARCH-REVIEW.md` — v0.0.1 架构审查报告格式参考

### Secondary (MEDIUM confidence)
- ruff 0.15.16 文档 — pyflakes (F) / flake8-bandit (S) / McCabe (C901) 规则行为

### Tertiary (LOW confidence)
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ruff 已安装并验证，检测结果已确认
- Architecture: HIGH — 审查流程清晰，16 模块分割可管理
- Pitfalls: HIGH — 基于实际 ruff 运行结果和项目文档确认

**Research date:** 2026-06-09
**Valid until:** 2026-07-09（代码审查方法稳定，30 天有效）
