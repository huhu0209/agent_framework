# Agent Framework

Python Agent 框架 — 统一 LLM 调用、工具编排、ReAct 推理、多 Agent 协作。**三层分离**：框架层（通用、可独立 `pip install`）→ 应用层（FastAPI）→ 前端（React）。

解决三个痛点：

- **Provider 碎片化** — 统一 ContentBlock 模型，一套代码切换 DeepSeek/OpenAI/Anthropic
- **重复造轮子** — 内置重试、流式解析、工具调用编排、上下文管理
- **缺少统一的 content block 模型** — 强制 content 为 ContentBlock 数组，消除 string|array 二义性

## 功能特性

- **LLM Adapter** — 统一接口对接 DeepSeek / OpenAI / Anthropic，自动重试 + Circuit Breaker + 流式
- **Tool System** — 注册/校验/路由/执行 + MCP 协议 + 内建工具 + 上下文压缩
- **Agent 策略** — ReAct 推理、Plan-and-Solve、反思改进、子 Agent 委派
- **Multi-Agent** — Teams 团队协作、Event Bus、A2A 跨框架互联
- **Safety** — 路径沙箱、四级权限、人机审批（HITL）、输出验证
- **Memory** — 双层存储、自动索引、LLM 评分检索、语义提取
- **扩展机制** — Skills 技能注册 + Slash 命令 + Hooks 生命周期钩子
- **编排与可视化** — Task 管理 + Orchestrator 引擎 + WebSocket 实时可视化 + 事件录制/回放
- **Web 前端** — React 19 单页应用：会话侧边栏、流式消息（Markdown / 工具调用块 / 思考块）、Inspector 运行时观测面板（config / system prompt / 工具链实时回放 + 离线降级）

## 架构总览

三层，依赖方向严格自上而下，应用层 editable 依赖框架，不反向依赖：

```
┌──────────────────────────────────────────────────┐
│  frontend/   React 19 + Vite + Tailwind          │  会话 UI + Inspector 观测面板
│              SSE 聊天流  +  WebSocket 观测通道     │
└─────────────────────┬────────────────────────────┘
                      │ HTTP /api/v1 (SSE)  +  WS :8765
┌─────────────────────▼────────────────────────────┐
│  backend/    FastAPI 应用层                       │  Agent 工厂 + Session + Redis
│              APP_AGENT_BACKEND=stub 可免 LLM      │
└─────────────────────┬────────────────────────────┘
                      │ editable 本地依赖
┌─────────────────────▼────────────────────────────┐
│  framework/  agent-framework-core (独立 pip 包)   │  LLM / Tools / Agents / 编排
└──────────────────────────────────────────────────┘
```

**框架内部分层：**

```
┌─────────────────────────────────────────┐
│  编排层    Orchestrator / Tasks / Viz   │  任务编排 + 可视化 + 录制
├─────────────────────────────────────────┤
│  Agent    ReAct / Plan-and-Solve        │  推理策略
│  策略     Reflection / Sub-Agent        │
│  多Agent  Teams / A2A                   │  团队协作
├─────────────────────────────────────────┤
│  扩展     Skills / Commands / Hooks     │  技能 + 命令 + 钩子
├─────────────────────────────────────────┤
│  Tools    Registry / Router / MCP       │  工具系统
│  Safety   沙箱 / 权限 / HITL / 验证     │  安全层
│  Memory   双层存储 / 索引 / 检索         │  记忆系统
│  Prompts  Profile / 模板组装            │  Prompt 管理
│  Transcript 会话录制 / 回放             │  转录层
├─────────────────────────────────────────┤
│  LLM      统一接口 + 3 Provider         │
│  Adapter  重试 + CB + 流式              │
└─────────────────────────────────────────┘
```

**设计原则：**
- 三层分离：框架层（`framework/`）→ 应用层（`backend/`）→ 前端（`frontend/`），框架可独立 `pip install`
- 每层只依赖下层，不反向依赖；backend 通过 uv workspace editable 装框架，改 framework 即时生效
- Provider 只做"跟一家模型对话"，路由/重试由上层负责
- 各家特有参数通过 `provider_extras` 透传，不做归一化

### 项目结构

```
framework/agent_framework/      独立框架包（agent-framework-core）
├── llm/           # LLM Adapter（3 Provider + 重试 + Circuit Breaker + 流式）
├── tools/         # Tool System（Registry / Router / MCP / 内建工具 / 上下文）
├── agents/        # Agent 策略（ReAct / Plan-and-Solve / Reflection / Sub-Agent）
├── teams/         # Multi-Agent（TeamManager / MessageBus）
├── a2a/           # Agent-to-Agent（Client / Server / AgentCard）
├── tasks/         # Task 管理（TaskManager / TaskRunner / RuntimeTask）
├── skills/        # 技能系统（Manifest / Registry / Discovery）
├── commands/      # Slash 命令分发
├── config/        # 配置层级（ConfigLoader / Settings / Merge）
├── hooks/         # 生命周期钩子
├── safety/        # 安全层（权限 / HITL / 命令策略 / 验证）
├── memory/        # 记忆系统（双层存储 + LLM 评分检索）
├── prompts/       # Prompt 管理（Profile / Assembler）
├── rules/         # 规则加载（RuleLoader / path-scoped filtering）
├── orchestrator/  # 编排引擎（OrchestratorEngine / PlanningSession / Worker）
├── viz/           # 可视化（EventBus / WebSocket / Recorder）
└── transcript/    # 会话转录（Reader / Writer / Consumer）

backend/                        FastAPI 应用（main.py:app）
├── main.py                     lifespan：Agent 工厂 + Redis(失败降级文件) + WS + 事件录制
├── app/api/v1/chat.py          聊天路由（SSE 流式 + 会话 CRUD）
├── app/services/               agent_factory / stub_factory / session(SessionManager + TTL)
├── app/config/                 Settings（env 最高优先，ConfigLoader 回退默认值）
└── tests/                      chat_api / cors / redis / session_* / stub_factory

frontend/                       React 19 + TS + Vite 8 + Tailwind 4
├── src/store.ts                zustand 全局状态（不可变更新 + zod 校验）
├── src/lib/wsClient.ts         Inspector WebSocket 客户端（重连 / 快照 / 离线降级）
├── src/components/
│   ├── ChatLayout.tsx          根布局（三栏）
│   ├── sidebar/                会话侧边栏（列表 / 搜索 / 重命名 / 删除）
│   ├── header/                 ChatHeader + ViewSwitcher / InspectButton / ModelChip
│   ├── composer/               ChatInput（Enter 发送 / Shift+Enter 换行）
│   ├── inspector/              运行时观测面板（Config / SystemPrompt / ToolChain 三分区）
│   ├── message/                消息流（Markdown / 工具调用块 / 思考块 / 建议卡）
│   └── markdown/               代码块 / 表格 / 锚点渲染增强
└── e2e/inspector.spec.ts       Playwright happy path（stub backend，免 LLM）
```

## 模块概览

| 模块 | 关键类 / 函数 | 说明 |
|------|---------------|------|
| `llm/` | `create_adapter`, `ResilientLLMAdapter`, `ILLMAdapter` | 统一 LLM 调用 + 重试/熔断/流式 |
| `tools/` | `ToolRegistry`, `ToolRouter`, `ToolExecutor`, `McpClient` | 工具注册/路由/执行/MCP |
| `agents/` | `Agent`, `AgentLoop`, `agent_from_config` | 推理策略（ReAct/PlanAndSolve/Reflection 见子模块） |
| `teams/` | `TeamManager`*, `MessageBus`* | 多 Agent 团队 |
| `a2a/` | `A2AClient`, `A2AServer`, `AgentCard` | 跨框架 Agent 互联 |
| `tasks/` | `TaskManager`, `TaskRunner`, `RuntimeTask` | 任务 DAG 管理 |
| `skills/` | `SkillRegistry`, `SkillManifest`, `SkillDiscovery` | 技能发现/注册 |
| `commands/` | `CommandDispatcher`, `SlashCommand` | Slash 命令 |
| `config/` | `ConfigLoader`, `Settings`, `merge_settings` | 配置层级加载/合并 |
| `hooks/` | `HookManager`, `HookEvent` | 生命周期钩子 |
| `safety/` | `PermissionPipeline`, `HITLManager`, `CommandPolicy`, `VerificationRunner` | 安全层 |
| `memory/` | `MemoryIndexManager`, `LLMScoringRetriever`, `MemoryStore` | 双层记忆 |
| `prompts/` | `AgentProfile`*, `PromptAssembler`* | Prompt 组装 |
| `rules/` | `RuleLoader` | 路径过滤规则 |
| `orchestrator/` | `OrchestratorEngine`, `PlanningSession`, `WorkerManager` | 编排引擎 |
| `viz/` | `AgentRunner`, `EventBus`, `serve_ws` | 实时可视化 + WS + 录制 |
| `transcript/` | `TranscriptReader`, `TranscriptWriter`, `TranscriptConsumer` | 会话录制/回放 |

> *`teams/`、`prompts/` 的 `__init__.py` 暂未做 barrel 导出，需走子模块路径（如 `agent_framework.teams.manager.TeamManager`）。

## Roadmap

| Milestone | Phases | Status |
|-----------|--------|--------|
| v0.0.1 彻底 Code Review | 1-5 | ✅ Shipped (2026-05-29, 687 tests) |
| v0.0.2 Agent 扩展与编排 | 6-8 | ✅ Shipped (2026-05-29, 812 tests) |
| v0.0.3 Agent 可视化平台 MVP | 9-11 | ✅ Shipped (2026-05-31, 964 tests) |
| v0.0.4 全面代码审查 | 12-14 | ✅ Shipped (2026-06-09, 964 tests) |
| v0.0.5 Review 问题修复 | 15-19 | ✅ Shipped (2026-06-10, 1002 tests) |
| v0.0.6 路径文件的统一 | 20-25 | ✅ Shipped (2026-06-12, 1146 tests) |

> 当前测试规模：framework 1237 例 / backend 68 例 / frontend 16 个单测文件 + 1 个 Playwright E2E。

## Quick Start

```bash
# === 框架层 ===
cd framework && uv pip install -e ".[test]"   # 安装框架（editable，含测试依赖）
cd framework && pytest tests/ -v               # 运行框架测试

# === 应用层（自动 editable 装框架）===
cd backend && uv pip install -e ".[test]"
cd backend && uvicorn main:app --reload --port 30002   # 真实 LLM 模式
cd backend && pytest tests/ -v                          # 后端测试

# stub 模式（联调前端 / 写 E2E，免真实 LLM key）
cd backend && APP_AGENT_BACKEND=stub APP_WS_ENABLED=true APP_WS_TOKEN=devtoken \
  APP_API_KEY=<key> APP_LLM_API_KEY=test uvicorn main:app --port 30002

# === 前端 ===
cd frontend && npm install
cd frontend && npm run dev          # vite dev，端口 30001，proxy /api + ws → 127.0.0.1:30002
cd frontend && npm run build        # tsc 类型检查 + vite 构建
cd frontend && npm run test         # vitest 单元/组件测试
cd frontend && npx playwright test  # E2E（自动起 stub backend + dev server）
```

关键环境变量见 `CLAUDE.md` 与各层 `.env.example`：`APP_API_KEY` / `APP_LLM_API_KEY` / `APP_AGENT_BACKEND`(stub|real) / `APP_WS_*`（backend）；`VITE_APP_API_KEY`（须与后端 `APP_API_KEY` 一致）/ `VITE_WS_URL`（frontend）。

## 技术栈

**框架层**（`agent-framework-core`）
- Python 3.11+
- Pydantic v2（数据模型与校验）
- httpx（异步 HTTP 客户端）、websockets、aiofiles、tavily-python

**应用层**（`backend/`）
- FastAPI + uvicorn
- pydantic-settings（env 配置）、redis[hiredis]（会话缓存，失败降级 JSONL）、aiofiles
- SSE 流式聊天 + 独立 WebSocket 观测通道（端口 8765）

**前端**（`frontend/`）
- React 19 + TypeScript + Vite 8
- Tailwind CSS 4 + Zustand（状态管理）+ zod（校验）
- react-markdown + remark-gfm + rehype-highlight/sanitize（Markdown 渲染）
- Vitest + @testing-library（单元/组件）+ Playwright（E2E）
