# Phase 5: 测试覆盖补充 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 5-测试覆盖补充
**Areas discussed:** TeamManager loop 深度测试, 安全边界 × 工具执行集成测试, PermissionPipeline 边界情况

---

## TeamManager loop 深度测试

### Q1: 如何控制时序？

| Option | Description | Selected |
|--------|-------------|----------|
| monkeypatch asyncio.sleep | 替换为立即返回的 mock，瞬间通过 idle 轮询 | ✓ |
| 缩短 sleep 时间 | 提取为可配置参数，测试时设 0.01s | |
| 真实等待 + 短超时 | max_idle_seconds=0.1，真实等 0.3s | |

**User's choice:** monkeypatch asyncio.sleep
**Notes:** 直接、可靠、不依赖真实时间

### Q2: 测试文件位置？

| Option | Description | Selected |
|--------|-------------|----------|
| 追加到 test_teams_manager.py | 用 TestTeamLoop class 分组 | ✓ |
| 新建 test_teams_loop.py | 专门测试 _loop 行为 | |

**User's choice:** 追加到现有文件
**Notes:** 文件只有 97 行，还有空间

### Q3: 测试粒度？

| Option | Description | Selected |
|--------|-------------|----------|
| 按行为拆分多个测试 | shutdown_via_inbox、idle_timeout 等独立测试 | ✓ |
| 单一大生命周期测试 | spawn → 处理 → idle → 超时关 | |

**User's choice:** 按行为拆分
**Notes:** 目标明确，失败时容易定位

### Q4: AgentLoop 处理方式？

| Option | Description | Selected |
|--------|-------------|----------|
| mock AgentLoop | 仅验证 _loop 内部行为，mock AgentLoop.run | ✓ |
| 真实 AgentLoop + FakeAdapter | 完整流程但依赖更多组件 | |

**User's choice:** mock AgentLoop
**Notes:** 仅验证 _loop 自身的 status 转换和 shutdown 响应

---

## 安全边界 × 工具执行集成测试

### Q1: 集成深度？

| Option | Description | Selected |
|--------|-------------|----------|
| AgentLoop 全链路 | 真实 AgentLoop + ToolRouter + FakeAdapter | ✓ |
| ToolRouter → safe_path | 不涉及 AgentLoop | |
| 两层都写 | 短链路 + 长链路 | |

**User's choice:** AgentLoop 全链路
**Notes:** 让 loop 调用 read_file("../../../etc/passwd")，验证最终返回 error 事件

### Q2: 测试文件位置？

| Option | Description | Selected |
|--------|-------------|----------|
| 追加到 test_builtin_tools.py | 和边界测试放在一起 | |
| 新建 test_safety_integration.py | 关注点清晰 | ✓ |
| 追加到 test_agent_loop.py | 测试主体是 AgentLoop | |

**User's choice:** 新建 test_safety_integration.py

### Q3: 覆盖场景数？

| Option | Description | Selected |
|--------|-------------|----------|
| 核心场景 2-3 个 | 路径遍历被拒、绝对路径被拒、正常访问 | ✓ |
| 全面覆盖 5+ 个 | 加错误消息不泄露、多步对话安全等 | |

**User's choice:** 核心场景
**Notes:** 边界细节已有单元测试覆盖，集成测试只验证链路通畅

---

## PermissionPipeline 边界情况

### Q1: 测试文件位置？

| Option | Description | Selected |
|--------|-------------|----------|
| 追加到 test_permissions.py | 用 TestEdgeCases class 分组 | ✓ |
| 新建 test_permission_integration.py | 区分单元和集成 | |

**User's choice:** 追加到 test_permissions.py

### Q2: 测试范围？

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 pipeline 边界 | 单元级边界测试，不涉及 ToolRouter | ✓ |
| pipeline + ToolRouter 集成 | 权限拒绝后 ToolRouter 阻断 | |

**User's choice:** 仅 pipeline 边界
**Notes:** pipeline 是纯同步代码，无需 async 测试

### Q3: 覆盖场景数？

| Option | Description | Selected |
|--------|-------------|----------|
| 4 个核心边界 | disallowed>allowed、无注解、CRITICAL_TOOLS 空、destructive+idempotent | ✓ |
| 2 个最小边界 | 只测冲突和无注解 | |

**User's choice:** 4 个核心边界

---

## Claude's Discretion

- monkeypatch asyncio.sleep 的具体实现方式
- FakeAdapter vs MockAdapter 的选择
- AgentLoop mock 的 setup 方式（side_effect 序列 vs return_value）
- 集成测试中 FakeAdapter 的 complete 返回值设计
- 具体测试函数命名

## Deferred Ideas

None — discussion stayed within phase scope
