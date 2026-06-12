# Phase 18: Backend 全面修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 18-Backend 全面修复
**Areas discussed:** SSE 错误响应策略, JSONL 原子写入 + 异步化, Framework 接口对接, session_id 验证 + Redis 异常

---

## SSE 错误响应策略

| Option | Description | Selected |
|--------|-------------|----------|
| 通用消息 | 所有异常统一返回 "An internal error occurred"，服务端记录完整 str(exc) | |
| 分类消息 | 区分已知错误（LLM 超时、Tool 执行失败）和未知错误，返回用户友好提示 | ✓ |
| 通用 + correlation ID | 返回通用消息 + UUID correlation ID 便于调试 | |

**User's choice:** 分类消息

| Option | Description | Selected |
|--------|-------------|----------|
| 仅分类 + 用户友好消息 | 客户端已知错误类型，可区分显示 | ✓ |
| 分类 + correlation ID | 附带服务端 UUID，便于用户反馈问题时后端查日志 | |

**User's choice:** 仅分类 + 用户友好消息

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 SSE 层替换 | session.messages 仍存储原始 str(exc)，只改传输层 | ✓ |
| SSE + messages 同步 | session.messages 也存储分类消息 | |

**User's choice:** 仅 SSE 层替换

| Option | Description | Selected |
|--------|-------------|----------|
| 基于异常类型映射 | isinstance 匹配，简单直接 | |
| 枚举 + 映射表 | ErrorCategory 枚举 + 用户友好消息映射表，更结构化可扩展 | ✓ |

**User's choice:** 枚举 + 映射表

---

## JSONL 原子写入 + 异步化

| Option | Description | Selected |
|--------|-------------|----------|
| 仅原子写入 | update_title/delete_session 改原子写入，_append_history 留后续 | |
| 原子写入 + asyncio.to_thread | 原子写入 + 同步 I/O 用 to_thread 包装 | |
| 原子写入 + aiofiles | 全部改 aiofiles async，与 Phase 16 framework 层一致 | ✓ |

**User's choice:** 原子写入 + aiofiles

| Option | Description | Selected |
|--------|-------------|----------|
| 全部改 async def | SessionManager 方法全部改为 async def，调用方 await | ✓ |
| 仅调用点 to_thread 包装 | SessionManager 内部仍同步，调用方负责异步化 | |

**User's choice:** 全部改 async def

| Option | Description | Selected |
|--------|-------------|----------|
| 全部 async | 内部方法也改 async，一致性最好 | ✓ |
| 仅文件 I/O 方法改 async | 其他保持同步 | |

**User's choice:** 全部 async

| Option | Description | Selected |
|--------|-------------|----------|
| aiofiles + os.replace | aiofiles 写 temp file + os.replace 原子替换 | ✓ |
| aiofiles 自带 os 替换 | 用 aiofiles.os 替换函数 | |

**User's choice:** aiofiles + os.replace

---

## Framework 接口对接

| Option | Description | Selected |
|--------|-------------|----------|
| 每次 create_loop 创建新 ctx | 将 ToolUseContext() 创建移到 create_loop 内部 | ✓ |
| deepcopy ctx | 用 copy.deepcopy 复制完整上下文 | |
| ToolUseContext.copy() 方法 | 框架层添加 copy() 方法 | |

**User's choice:** 每次 create_loop 创建新 ctx

| Option | Description | Selected |
|--------|-------------|----------|
| AgentLoop 公共 property | 添加 @property system_prompt_text，最小改动 | ✓ |
| create_loop 返回值包含 | 返回 (loop, system_prompt_text) 元组 | |
| TranscriptConsumer 自行获取 | consumer 自行获取 system prompt | |

**User's choice:** AgentLoop 公共 property

| Option | Description | Selected |
|--------|-------------|----------|
| 每会话独立 workspace | 每个会话有独立工作目录 | |
| 共享 workspace 目录 | storage_dir / "shared_workspace"，所有会话共享 | ✓ |
| 保持默认 | 不改 working_dir | |

**User's choice:** 共享 workspace 目录

| Option | Description | Selected |
|--------|-------------|----------|
| 添加公共 persist/restore 方法 | 封装 Redis + JSONL 操作 | ✓ |
| 仅移除下划线前缀 | 重命名为公共方法 | |

**User's choice:** 添加公共 persist/restore 方法

---

## session_id 验证 + Redis 异常

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI Path() 验证 | 每个端点独立声明 pattern，FastAPI 自动返回 422 | ✓ |
| FastAPI Depends 依赖注入 | 集中管理验证逻辑 | |
| SessionManager 内部验证 | 在 manager 层统一验证 | |

**User's choice:** FastAPI Path() 验证

| Option | Description | Selected |
|--------|-------------|----------|
| 区分异常类型 | ConnectionError/TimeoutError 降级运行，ValueError 启动失败 | ✓ |
| ERROR 日志 + banner | 降级运行但打印 banner 提示 | |
| 启动失败 | 无 Redis 时应用不启动 | |

**User's choice:** 区分异常类型

| Option | Description | Selected |
|--------|-------------|----------|
| 改 SecretStr | llm_api_key 改 SecretStr，调用方用 get_secret_value() | ✓ |
| 保持 str + 注释 | 仅添加注释说明风险 | |

**User's choice:** 改 SecretStr

| Option | Description | Selected |
|--------|-------------|----------|
| 收紧 methods/headers | methods=[GET,POST,DELETE,PATCH]，headers=[Content-Type, X-Session-Id] | ✓ |
| 仅收紧 headers | methods 保持 wildcard | |

**User's choice:** 收紧 methods/headers

---

## Claude's Discretion

- ErrorCategory 枚举的具体定义和命名
- 用户友好消息的具体文案
- SessionManager 异步化的具体方法拆分和调用链更新
- persist/restore 方法的具体 API 设计
- FastAPI Path() pattern 的具体写法
- 每个 plan 内部的修复顺序

## Deferred Ideas

- BKND-SEC-06 (全部 API 无认证) — 需单独 milestone，架构级改动
- BKND-ARCH-04 (SessionManager 混合职责) — 需较大重构
- BKND-ARCH-05 (redis_client 类型安全) — Protocol 类型改进
- BKND-LOGIC-05 (get() 刷新 TTL) — LOW 级别设计决策
