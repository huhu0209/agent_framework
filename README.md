# Agent Framework

一个 Python Agent 框架，提供统一的 LLM 调用接口、工具系统、ReAct 推理循环和记忆系统。

写这个框架解决三个痛点：

- **Provider 碎片化** — DeepSeek、OpenAI、Anthropic 各家 API 格式不同，切换成本高。框架用统一的 ContentBlock 模型消除差异，一套代码无缝切换。
- **重复造轮子** — 重试策略、流式解析、工具调用编排每次都重写。框架内置指数退避重试、Circuit Breaker、SSE 流解析器。
- **缺少统一的 content block 模型** — OpenAI 的 `string | array` 二义性容易踩坑。框架强制 `content` 永远是 `ContentBlock` 数组。

## 架构总览

```
用户代码
    │
    ▼
┌─────────────────────────────────────┐
│  agents/        ReAct Agent Loop    │  推理循环 + 工具调用编排
│  prompts/       Prompt 模板组装     │  AgentProfile + 模块化 prompt
├─────────────────────────────────────┤
│  tools/         Tool System         │  注册、校验、路由、执行、MCP
│  safety/        安全层              │  沙箱、权限、HITL、验证
│  memory/        记忆系统            │  索引、检索、语义提取、写入
├─────────────────────────────────────┤
│  llm/           LLM Adapter         │  统一接口 + 3 Provider
│                 retry + CB           │  指数退避重试 + Circuit Breaker
└─────────────────────────────────────┘
```

**设计原则：**
- 框架层（`framework/`）与应用层（`backend/`）分离，框架可独立 `pip install`
- 每层只依赖下层，不反向依赖
- Provider 只做"跟一家模型对话"，路由/重试由上层负责
- 各家特有参数通过 `provider_extras` 透传，不做归一化

### 项目结构

```
agent_framework/
├── framework/agent_framework/    ← 独立框架包
│   ├── llm/                      # LLM Adapter（统一接口 + 3 Provider）
│   ├── tools/                    # Tool System（注册、路由、MCP）
│   ├── agents/                   # ReAct Agent Loop
│   ├── safety/                   # 安全层（沙箱、权限、HITL）
│   ├── memory/                   # 记忆系统（索引、检索、语义提取）
│   ├── prompts/                  # Prompt 模板组装
│   └── orchestrator/             # 编排器
├── backend/                      ← 应用层（使用框架）
├── frontend/                     ← React 前端（脚手架阶段）
└── docs/plans/                   # 设计文档
```

## 核心模块

### LLM Adapter — 统一多 Provider 调用

```python
from agent_framework.llm import create_adapter, CompletionConfig, UserMessage, TextBlock

adapter = create_adapter(
    provider="deepseek",
    api_key="your-api-key",
    model="deepseek-chat",
)

# 非流式
config = CompletionConfig(
    model="deepseek-chat",
    messages=[UserMessage(content=[TextBlock(text="你好")])],
)
result = await adapter.complete(config)
print(result.content[0].text)

# 流式
config.stream = True
async for event in adapter.stream(config):
    if event.type == "text_delta":
        print(event.data["text"], end="")
```

**Provider 支持：**

| Provider | 协议 | 特殊处理 |
|----------|------|---------|
| DeepSeek | OpenAI ChatCompletions | `reasoning_content`、thinking 模式 |
| OpenAI | Chat Completions | `reasoning_effort`、structured output、vision |
| Anthropic | Messages API | system 顶层字段、content block tool_use、extended thinking |

**统一接口 `ILLMAdapter`：**

```python
class ILLMAdapter(ABC):
    async def complete(self, config: CompletionConfig) -> CompletionResult: ...
    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]: ...
    def get_provider_info(self) -> ProviderInfo: ...
    async def health_check(self) -> bool: ...
```

`create_adapter` 自动包装为 `ResilientLLMAdapter`，内置 429 重试（读 `retry-after` header）+ 5xx 指数退避 + Circuit Breaker。

### Tool System — 工具注册与执行

```python
from agent_framework.tools import ToolRegistry, ToolRouter, ToolSpec
from agent_framework.llm import ToolParameterSchema

registry = ToolRegistry()

registry.register(ToolSpec(
    name="get_weather",
    description="获取指定城市的天气",
    parameters=ToolParameterSchema(
        type="object",
        properties={"city": {"type": "string", "description": "城市名"}},
        required=["city"],
    ),
    handler=get_weather_handler,
))

# ToolRouter 负责调度：解析 LLM 返回的 tool_use → 匹配 handler → 执行 → 返回结果
router = ToolRouter(registry=registry)
result = await router.dispatch(tool_call, context)
```

支持内建工具、MCP 工具（`McpManager`）、Agent 工具三种来源。`ToolValidator` 在执行前校验参数，`PermissionPipeline` 实现 DENY → MODE → ALLOW → ASK 四级权限控制。

### Agent Loop — ReAct 推理循环

```python
from agent_framework.agents import AgentLoop
from agent_framework.prompts import AgentProfile

profile = AgentProfile(
    name="assistant",
    description="通用助手",
    soul="你是一个有帮助的AI助手",
)

loop = AgentLoop(
    adapter=adapter,
    profile=profile,
    tool_router=router,
    max_steps=10,
)

async for event in loop.run("帮我查一下北京天气"):
    if event.type == "tool_result":
        print(f"Tool {event.data['name']}: {event.data['result']}")
    elif event.type == "done":
        print(event.data["response"])
```

AgentLoop 驱动多轮 tool calling 循环：LLM 返回 `tool_use` → 执行工具 → 结果回传 LLM → 直到 LLM 不再调用工具或达到 `max_steps`。

### 其他模块

- **Safety** (`safety/`) — 路径沙箱（防 workspace 逃逸 + symlink bypass）、`PermissionPipeline` 四级权限、`HITLManager` 人机交互审批、`VerificationRunner` 工具输出正则验证
- **Memory** (`memory/`) — 双层存储（episodic + semantic）、`MemoryIndexManager` 自动维护 MEMORY.md、`LLMScoringRetriever` 相关性评分检索、`SemanticExtractor` 从对话提取长期记忆
- **Prompts** (`prompts/`) — `AgentProfile` 定义 Agent 灵魂、`PromptAssembler` 模块化组装 system prompt

## Roadmap

| Phase | 模块 | 状态 |
|-------|------|------|
| 1-6 | 核心框架（LLM / Tools / Agents / Safety / Memory / Prompts） | ✅ 已完成 |
| 7 | Skills — 知识注入 | 📋 计划中 |
| 8 | Slash Commands — 用户交互入口 | 📋 计划中 |
| 9 | Hooks — 生命周期扩展 | 📋 计划中 |
| 10 | Plugin — 打包分发 | 📋 计划中 |
| 11 | Error Recovery + Task | 📋 计划中 |
| 12 | Multi-Agent + A2A | 📋 计划中 |

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
