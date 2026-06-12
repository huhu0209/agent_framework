# Agent Framework

Python Agent 框架 — 统一 LLM 调用、工具编排、ReAct 推理、多 Agent 协作。

解决三个痛点：

- **Provider 碎片化** — 统一 ContentBlock 模型，一套代码切换 DeepSeek/OpenAI/Anthropic
- **重复造轮子** — 内置重试、流式解析、工具调用编排、上下文管理
- **缺少统一的 content block 模型** — 强制 content 为 ContentBlock 数组，消除 string|array 二义性

## 功能特性

- **LLM Adapter** — 统一接口对接 DeepSeek / OpenAI / Anthropic，自动重试 + Circuit Breaker
- **Tool System** — 注册/校验/路由/执行 + MCP 协议 + 内建工具 + 上下文压缩
- **Agent 策略** — ReAct 推理、Plan-and-Solve、反思改进、子 Agent 委派
- **Multi-Agent** — Teams 团队协作、Event Bus、A2A 跨框架互联
- **Safety** — 路径沙箱、四级权限、人机审批（HITL）、输出验证
- **Memory** — 双层存储、自动索引、LLM 评分检索、语义提取
- **扩展机制** — Skills 技能注册 + Slash 命令 + Hooks 生命周期钩子
- **编排与可视化** — Task 管理 + Orchestrator 引擎 + WebSocket 实时可视化

## 架构总览

```
用户代码
    │
    ▼
┌─────────────────────────────────────────┐
│  编排层    Orchestrator / Tasks / Viz   │  任务编排 + 可视化
├─────────────────────────────────────────┤
│  Agent    ReAct / Plan-and-Solve        │  推理策略
│  策略     Reflection / Sub-Agent        │
│  多Agent  Teams / A2A                   │  团队协作
├─────────────────────────────────────────┤
│  扩展     Skills / Commands / Hooks     │  技能 + 命令 + 钩子
├─────────────────────────────────────────┤
│  Tools    Registry / Router / MCP       │  工具系统
│  Safety   沙箱 / 权限 / HITL / 验证    │  安全层
│  Memory   双层存储 / 索引 / 检索        │  记忆系统
│  Prompts  Profile / 模板组装            │  Prompt 管理
├─────────────────────────────────────────┤
│  LLM      统一接口 + 3 Provider         │
│  Adapter  重试 + CB + 流式              │
└─────────────────────────────────────────┘
```

**设计原则：**
- 框架层（`framework/`）与应用层（`backend/`）分离，框架可独立 `pip install`
- 每层只依赖下层，不反向依赖
- Provider 只做"跟一家模型对话"，路由/重试由上层负责
- 各家特有参数通过 `provider_extras` 透传，不做归一化

### 项目结构

```
framework/agent_framework/
├── llm/           # LLM Adapter（3 Provider + 重试 + 流式）
├── tools/         # Tool System（Registry / MCP / 内建工具 / 上下文）
├── agents/        # Agent 策略（ReAct / Plan-and-Solve / Reflection / Sub-Agent）
├── teams/         # Multi-Agent（Teams Manager / Event Bus）
├── a2a/           # Agent-to-Agent（Client / Server / Models）
├── tasks/         # Task 管理（Manager / Runner）
├── skills/        # 技能系统（Manifest / Registry）
├── commands/      # Slash 命令路由
├── config/        # 配置层级（ConfigLoader / Settings / Merge）
├── hooks/         # 生命周期钩子
├── safety/        # 安全层
├── memory/        # 记忆系统
├── prompts/       # Prompt 管理
├── rules/         # 规则加载（RuleLoader / path-scoped filtering）
├── orchestrator/  # 编排引擎
└── viz/           # 可视化（WebSocket / Event Bus）
```

## 模块概览

| 模块 | 关键类 | 说明 |
|------|--------|------|
| `llm/` | `create_adapter`, `ILLMAdapter`, `ResilientLLMAdapter` | 统一 LLM 调用 + 重试 |
| `tools/` | `ToolRegistry`, `ToolRouter`, `McpClient` | 工具注册/路由/MCP |
| `agents/` | `AgentLoop`, `PlanAndSolveAgent`, `ReflectionAgent` | 推理策略 |
| `teams/` | `TeamManager`, `MessageBus` | 多 Agent 团队 |
| `a2a/` | `A2AClient`, `A2AServer` | 跨框架 Agent 互联 |
| `tasks/` | `TaskManager`, `TaskRunner` | 任务管理 |
| `skills/` | `SkillRegistry`, `SkillManifest` | 技能注册与加载 |
| `commands/` | `CommandDispatcher` | Slash 命令 |
| `config/` | `ConfigLoader`, `Settings` | 配置层级加载与合并 |
| `hooks/` | `HookManager` | 生命周期钩子 |
| `safety/` | `PermissionPipeline`, `HITLManager`, `CommandPolicy` | 安全层 |
| `memory/` | `MemoryIndexManager`, `LLMScoringRetriever` | 记忆系统 |
| `prompts/` | `AgentProfile`, `PromptAssembler` | Prompt 管理 |
| `rules/` | `RuleLoader` | 路径过滤规则加载 |
| `orchestrator/` | `OrchestratorEngine`, `Planner` | 编排引擎 |
| `viz/` | `AgentRunner`, `EventBus` | 实时可视化 |

## Roadmap

| Milestone | Phases | Status |
|-----------|--------|--------|
| v0.0.1 彻底 Code Review | 1-5 | ✅ Shipped (2026-05-29, 687 tests) |
| v0.0.2 Agent 扩展与编排 | 6-8 | ✅ Shipped (2026-05-29, 812 tests) |
| v0.0.3 Agent 可视化平台 MVP | 9-11 | ✅ Shipped (2026-05-31, 964 tests) |
| v0.0.4 全面代码审查 | 12-14 | ✅ Shipped (2026-06-09, 964 tests) |
| v0.0.5 Review 问题修复 | 15-19 | ✅ Shipped (2026-06-10, 1002 tests) |
| v0.0.6 路径文件的统一 | 20-25 | ✅ Shipped (2026-06-12, 1146 tests) |

## Quick Start

```bash
# 安装框架（含测试依赖）
cd framework
uv pip install -e ".[test]"

# 运行测试
pytest tests/ -v

# 安装应用层（自动安装框架依赖）
cd ../backend
uv pip install -e ".[test]"

# 前端开发
cd ../frontend
npm install
npm run dev
```

## 技术栈

**后端**
- Python 3.11+
- FastAPI
- httpx（异步 HTTP 客户端）
- Pydantic v2（数据模型与校验）

**前端**（脚手架阶段）
- Vite + React + TypeScript
- Tailwind CSS
