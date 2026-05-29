# Agent Framework — PROJECT.md

## Project Overview

Python Agent 框架，Orchestrator 模式。框架层（通用、可复用）和应用层（具体业务）分离。
核心已实现：LLM Adapter（3 Provider）、Tool System、ReAct Agent Loop、Safety、Memory、Prompts、Skills、Tasks、Teams、Hooks、Commands。

## Tech Stack

- **Framework:** Python 3.11+, Pydantic v2, httpx, asyncio
- **Backend:** FastAPI（脚手架）
- **Frontend:** Vite + React + TypeScript + Tailwind（脚手架）
- **Test:** pytest, pytest-asyncio

## Milestone History

### v0.0.1 — 彻底 Code Review（已完成）

**目标：** 对框架层全部已实现代码做系统性 Code Review，产出结构化审查报告，修复关键问题。

**完成状态：** 5 个阶段全部完成。687 测试通过，Bug 修复 3 项、安全修复 3 项、架构审查报告、性能审查报告、测试覆盖补充 12 个新测试。

**背景：** 框架已完成 6 大模块 + 5 个扩展模块（Skills、Tasks、Teams、Hooks、Commands），共 ~7600 行源码、630+ 测试。全面审查后提升至 687 测试。

**范围：**
- 仅框架层（`framework/agent_framework/`）
- 不涉及 backend/frontend（脚手架阶段）
- 不涉及新功能开发

**已有的代码库分析：**
- `.planning/codebase/ARCHITECTURE.md` — 架构分析
- `.planning/codebase/CONCERNS.md` — 已知问题清单（Tech Debt / Bugs / Security / Performance / Fragile Areas / Test Gaps）
- `.planning/codebase/CONVENTIONS.md` — 编码规范
- `.planning/codebase/TESTING.md` — 测试规范
- `.planning/codebase/STRUCTURE.md` — 文件结构
- `.planning/codebase/STACK.md` — 技术栈
- `.planning/codebase/INTEGRATIONS.md` — 依赖关系
