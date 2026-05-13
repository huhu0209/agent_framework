# Resilient Adapter 设计

将 retry.py 中已实现的 `retry_with_backoff()` 和 `CircuitBreaker` 集成到 Provider 层。

## 方案

组合式包装器 + 工厂函数。不改动现有 Provider 代码。

## 新文件

### `llm/resilient.py`

**`ResilientLLMAdapter`** — 实现 `ILLMAdapter`，内部组合：
- `_provider: ILLMAdapter` — 被包装的底层 provider
- `_retry_config: RetryConfig`
- `_breaker: CircuitBreaker`

调用流程：
```
complete() / stream()
  → breaker.allow_request()   # 拒绝则抛 CircuitOpenError
  → retry_with_backoff(fn)    # 带退避重试
    → fn = provider.complete / provider.stream
  → breaker.record_success / record_failure
```

stream() 同样保护：重试时重新发起流请求，breaker 打开时拒绝。

**`create_adapter()`** — 工厂函数：
```python
def create_adapter(
    provider: str,           # "deepseek" | "openai" | "anthropic"
    api_key: str,
    model: str,
    base_url: str | None = None,
    retry_config: RetryConfig = RetryConfig(),
    breaker_config: CircuitBreakerConfig = CircuitBreakerConfig(),
) -> ResilientLLMAdapter
```

## 修改文件

### `llm/base.py`

新增 `CircuitOpenError` 异常，继承 `LLMAdapterError`。

### `llm/__init__.py`

新增导出 `ResilientLLMAdapter`, `create_adapter`, `CircuitOpenError`。

## 不改动

- 所有 Provider 实现（DeepSeek, OpenAI, Anthropic）
- `retry.py`
- `types.py`

## 文件结构变化

```
llm/
├── base.py           # + CircuitOpenError
├── retry.py          # 不变
├── resilient.py      # 新：ResilientLLMAdapter + create_adapter
├── providers/        # 不变
└── __init__.py       # + 导出
```

## 使用示例

```python
# 创建
adapter = create_adapter(provider="deepseek", api_key="...", model="deepseek-chat")

# 兼容 OpenAI 格式的其他厂商
adapter = create_adapter(
    provider="openai",
    api_key="sk-xxx",
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 普通调用
result = await adapter.complete(messages)

# 流式调用
async for event in await adapter.stream(messages):
    ...

# health_check — 包含 breaker 状态
health = await adapter.health_check()
```
