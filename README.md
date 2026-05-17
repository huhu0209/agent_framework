# Agent Framework

Orchestrator 模式的 Agent 系统，统一多 LLM Provider 调用接口。

## 技术栈

**后端**
- Python 3.11+
- FastAPI
- httpx（异步 HTTP 客户端）
- Pydantic v2（数据模型与校验）

**前端**（脚手架阶段）
- Vite 8 + React 19 + TypeScript 6
- Tailwind CSS 4

## 项目结构

```
agent_framework/
├── framework/                    ← 通用框架包（pip install -e）
│   ├── agent_framework/
│   │   ├── llm/                  # LLM Adapter 层（已实现）
│   │   │   ├── base.py           # ILLMAdapter 抽象接口 + 异常体系
│   │   │   ├── types.py          # 统一类型定义（消息、ContentBlock、配置、结果）
│   │   │   ├── transform.py      # Provider 请求/响应转换
│   │   │   ├── streaming.py      # SSE 解析 + OpenAI delta 流解析器
│   │   │   ├── retry.py          # 指数退避重试 + Circuit Breaker
│   │   │   ├── resilient.py      # ResilientLLMAdapter 包装器 + 工厂函数
│   │   │   └── providers/
│   │   │       ├── deepseek_provider.py
│   │   │       ├── openai_provider.py
│   │   │       └── anthropic_provider.py
│   │   ├── tools/                # Tool System（已实现）
│   │   ├── agents/               # ReAct Agent Loop（已实现）
│   │   ├── memory/               # 记忆系统（脚手架）
│   │   ├── orchestrator/         # 编排器（脚手架）
│   │   └── prompts/              # Prompt 模板（脚手架）
│   ├── tests/
│   └── pyproject.toml
├── backend/                      ← 应用层（使用框架）
│   ├── app/
│   │   ├── api/                  # API 路由（待实现）
│   │   ├── config/               # 配置管理（待实现）
│   │   ├── models/               # 数据模型（待实现）
│   │   ├── services/             # 业务服务（待实现）
│   │   └── utils/                # 工具函数（待实现）
│   ├── pyproject.toml            # 依赖本地 framework
│   └── main.py
├── frontend/                     # React 前端（脚手架阶段）
├── docs/
│   └── plans/                    # 设计与实现计划
└── DESIGN.md                     # Claude/Anthropic 风格设计系统
```

## LLM Adapter 层

### 架构

```
用户代码
    │
    ▼
create_adapter("deepseek", ...)  ← 工厂函数
    │
    ▼
ResilientLLMAdapter             ← retry + circuit breaker 包装
    │
    ▼
DeepSeekProvider / OpenAIProvider / AnthropicProvider
    │
    ▼
transform.py                    ← 统一格式 ↔ Provider 格式转换
    │
    ▼
httpx (HTTP 请求)
```

**设计原则：**
- 各 Provider 只做"跟一家模型对话"，路由和重试由上层负责
- `content` 永远是 `ContentBlock` 数组，消除 OpenAI 的 `string | array` 二义性
- `tool_use` / `tool_result` 按 Anthropic 的 content block 方式建模
- 各家特有参数通过 `provider_extras` 透传，不做归一化

### Provider 体系

| Provider | 协议 | 特殊处理 |
|----------|------|---------|
| DeepSeek | OpenAI ChatCompletions | `reasoning_content` 回传、thinking 模式、不支持 vision |
| OpenAI | Chat Completions | `reasoning_effort`、structured output、vision |
| Anthropic | Messages API | system 顶层字段、content block tool_use、extended thinking + signature |

所有 Provider 实现统一接口 `ILLMAdapter`：

```python
class ILLMAdapter(ABC):
    async def complete(self, config: CompletionConfig) -> CompletionResult: ...
    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]: ...
    def get_provider_info(self) -> ProviderInfo: ...
    async def health_check(self) -> bool: ...
```

### 使用示例

```python
from agent_framework.llm import create_adapter

# 创建 adapter
adapter = create_adapter(
    provider="deepseek",
    api_key="your-api-key",
    model="deepseek-chat",
)

# 非流式调用
from agent_framework.llm import UserMessage, TextBlock, CompletionConfig

config = CompletionConfig(
    model="deepseek-chat",
    messages=[
        UserMessage(content=[TextBlock(text="你好")]),
    ],
)
result = await adapter.complete(config)
print(result.content[0].text)

# 流式调用
config.stream = True
async for event in adapter.stream(config):
    if event.type == "text_delta":
        print(event.data["text"], end="")
```

### 类型系统

**ContentBlock 类型：**

| 类型 | 用途 |
|------|------|
| `TextBlock` | 文本内容 |
| `ImageBlock` | 图片（base64 或 URL） |
| `ToolUseBlock` | 工具调用（assistant 发起） |
| `ToolResultBlock` | 工具返回结果（user 回传） |
| `ThinkingBlock` | 思考过程（Anthropic/DeepSeek） |

**消息类型：** `SystemMessage`、`UserMessage`、`AssistantMessage`、`ToolMessage`

**流式事件：** `text_delta`、`thinking_delta`、`tool_use_start/delta/end`、`usage`、`done`、`error`、`raw`

### Resilient 机制

**重试策略（retry.py）：**
- 429 → 读取 `retry-after` header → 指数退避 + jitter
- 5xx → 指数退避，最多 3 次
- 400 → 不重试

**Circuit Breaker：**
- 连续 N 次失败 → 熔断（拒绝请求）
- 冷却期后 half-open 探测
- 探测成功 → 恢复

**工厂函数 `create_adapter`：**
自动将 Provider 包装为 `ResilientLLMAdapter`，内置 retry + circuit breaker。

## 开发指南

### 安装

```bash
# 框架
cd framework
uv pip install -e ".[test]"

# 应用（自动安装框架依赖）
cd backend
uv pip install -e ".[test]"

# 前端
cd frontend
npm install
```

### 测试

```bash
cd framework
pytest tests/ -v
```

### 前端开发

```bash
cd frontend
npm run dev
```
