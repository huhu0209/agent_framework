# Roadmap: Agent Framework

## Milestones

- ✅ **v0.0.1 彻底 Code Review** — Phases 1-5 (shipped 2026-05-29)
- ✅ **v0.0.2 Agent 扩展与编排** — Phases 6-8 (shipped 2026-05-29)
- ✅ **v0.0.3 Agent 可视化平台 MVP** — Phases 9-11 (shipped 2026-05-31)
- ✅ **v0.0.4 全面代码审查** — Phases 12-14 (shipped 2026-06-09)
- 🔄 **v0.0.5 Review 问题修复** — Phases 15-19 (in progress)

## Phases

<details>
<summary>✅ v0.0.1 彻底 Code Review (Phases 1-5) — SHIPPED 2026-05-29</summary>

- [x] Phase 1: Bug 修复审查 (3/3 plans) — completed
- [x] Phase 2: 安全审查与修复 (2/2 plans) — completed
- [x] Phase 3: 架构与代码质量审查 (2/2 plans) — completed
- [x] Phase 4: 性能与数据安全审查 (1/1 plan) — completed
- [x] Phase 5: 测试覆盖补充 (4/4 plans) — completed

</details>

<details>
<summary>✅ v0.0.2 Agent 扩展与编排 (Phases 6-8) — SHIPPED 2026-05-29</summary>

- [x] Phase 6: Agent 类型扩展 (3/3 plans) — completed 2026-05-29
- [x] Phase 7: 编排引擎 + 配置化 + 搜索 (3/3 plans) — completed 2026-05-29
- [x] Phase 8: A2A 协议 (3/3 plans) — completed 2026-05-29

</details>

<details>
<summary>✅ v0.0.3 Agent 可视化平台 MVP (Phases 9-11) — SHIPPED 2026-05-31</summary>

- [x] Phase 9: Backend 事件系统 (3/3 plans) — completed 2026-05-29
- [x] Phase 10: Frontend Canvas 渲染 (3/3 plans) — completed 2026-05-30
- [x] Phase 11: Frontend React 集成 (3/3 plans) — completed 2026-05-31

</details>

<details>
<summary>✅ v0.0.4 全面代码审查 (Phases 12-14) — SHIPPED 2026-06-09</summary>

- [x] Phase 12: Framework 代码审查 (5/5 plans) — completed 2026-06-09
- [x] Phase 13: Backend 代码审查 (2/2 plans) — completed 2026-06-09
- [x] Phase 14: Frontend 代码审查 (2/2 plans) — completed 2026-06-09

</details>

<details>
<summary>🔄 v0.0.5 Review 问题修复 (Phases 15-19) — IN PROGRESS</summary>

### Phase 15: Framework 死代码与快速修复
**Goal:** 清理所有未使用 import，修复 logger 未定义，零 ruff F401/F821 warning
**Requirements:** FW-DEAD-01~06, FW-SEC-01
**Success Criteria:**
1. `ruff check --select F401,F821 framework/` 输出为空
2. `agent_loop.py` logger 正确定义，memory flush 异常可被正确记录
3. `from __future__ import annotations` 或 httpx import 位置修复
4. 全部 964+ 测试通过
**Plans:** 1/1 plans complete

Plans:
- [x] 15-01-PLAN.md — Remove 32 unused imports, fix logger undefined, fix httpx TYPE_CHECKING

**Depends on:** None

### Phase 16: Framework 安全修复
**Goal:** 修复安全漏洞 — 同步 I/O、MCP 环境变量、注入防护、WebSocket 认证
**Requirements:** FW-SEC-02~09
**Success Criteria:**
1. memory/ 模块所有文件 I/O 改为 async（aiofiles 或 to_thread）
2. MCP 子进程仅继承白名单环境变量
3. Skill 内容转义处理，profile prompt 注入防护
4. WebSocket 添加 token 认证（可配置）
5. try-except-pass 改为 logger.warning/debug 记录
6. 全部 964+ 测试通过
**Plans:** 4/4 plans complete

Plans:
- [x] 16-01-PLAN.md — memory/ + result_truncator 同步 I/O 改 aiofiles async (FW-SEC-02, FW-SEC-07)
- [x] 16-02-PLAN.md — MCP 环境变量白名单 + 敏感 key 过滤扩展 (FW-SEC-03, FW-SEC-08)
- [x] 16-03-PLAN.md — PromptAssembler XML 标签 + Skill 边界标记 (FW-SEC-04, FW-SEC-05)
- [x] 16-04-PLAN.md — WebSocket token 认证 + try-except-pass 修复 (FW-SEC-06, FW-SEC-09)

**Depends on:** Phase 15

### Phase 17: Framework 逻辑与架构修复
**Goal:** 修复逻辑漏洞、降低复杂度、增强验证器
**Requirements:** FW-LOGIC-01~10
**Success Criteria:**
1. ASK 权限决策触发 HITL 机制（非返回 error）
2. _CRITICAL_TOOLS 改为可配置
3. AgentLoop.run C901 从 30 降到 <20
4. ToolRouter.dispatch 拆分为管道模式，C901 从 18 降到 <10
5. search_tools 消除模块级全局可变状态
6. ToolValidator 增加 enum 和 unknown 参数验证
7. 全部 964+ 测试通过
**Plans:** 4/4 plans complete

Plans:
- [x] 17-01-PLAN.md — _CRITICAL_TOOLS 构造注入 + ToolValidator enum/unknown + TypedDict extra + MCP 文档 (FW-LOGIC-02,06,07,10)
- [x] 17-02-PLAN.md — SearchClient 类封装消除全局可变状态 (FW-LOGIC-05)
- [x] 17-03-PLAN.md — HITLManager 注入 ToolRouter + dispatch 复杂度拆分 + 移除 _dispatch_agent (FW-LOGIC-01,04,08)
- [x] 17-04-PLAN.md — AgentLoop.run 复杂度拆分 + _apply_changes 复杂度拆分 (FW-LOGIC-03,09)

**Depends on:** Phase 16

### Phase 18: Backend 全面修复
**Goal:** 修复 Backend 安全和逻辑问题
**Requirements:** BK-SEC-01~05, BK-LOGIC-01~05
**Success Criteria:**
1. SSE 异常返回通用错误消息，不泄漏内部信息
2. session_id path 参数统一验证（SESSION_ID_RE）
3. CORS methods/headers 收紧为实际使用列表
4. JSONL 写入改为原子模式（write temp + os.replace）
5. Shared ToolUseContext 改为每会话独立实例
6. AgentFactory 设置 working_dir
7. 不再访问 framework 私有属性
8. 全部 964+ 测试通过
**Depends on:** Phase 17 (framework 接口变更可能影响 backend)

### Phase 19: Frontend 全面修复
**Goal:** 修复 Frontend 安全、逻辑和架构问题
**Requirements:** FT-SEC-01~02, FT-LOGIC-01~04, FT-ARCH-01~05
**Success Criteria:**
1. SSE event payload 添加 zod schema 验证
2. react-markdown 添加 rehype-sanitize
3. res.body null 检查 + JSON.parse 错误处理
4. 消息列表自动滚动到底部
5. hoverRef timeout 组件卸载清理
6. store 错误处理添加用户反馈
7. 内联 hover 样式替换为 Tailwind
8. `npm run build` 成功，无 TypeScript 错误
**Depends on:** Phase 18 (SSE 格式变更可能影响前端)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug 修复审查 | v0.0.1 | 3/3 | Complete | 2026-05-28 |
| 2. 安全审查与修复 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 3. 架构与代码质量审查 | v0.0.1 | 2/2 | Complete | 2026-05-28 |
| 4. 性能与数据安全审查 | v0.0.1 | 1/1 | Complete | 2026-05-29 |
| 5. 测试覆盖补充 | v0.0.1 | 4/4 | Complete | 2026-05-29 |
| 6. Agent 类型扩展 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 7. 编排引擎 + 配置化 + 搜索 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 8. A2A 协议 | v0.0.2 | 3/3 | Complete | 2026-05-29 |
| 9. Backend 事件系统 | v0.0.3 | 3/3 | Complete | 2026-05-29 |
| 10. Frontend Canvas 渲染 | v0.0.3 | 3/3 | Complete | 2026-05-30 |
| 11. Frontend React 集成 | v0.0.3 | 3/3 | Complete | 2026-05-31 |
| 12. Framework 代码审查 | v0.0.4 | 5/5 | Complete | 2026-06-09 |
| 13. Backend 代码审查 | v0.0.4 | 2/2 | Complete | 2026-06-09 |
| 14. Frontend 代码审查 | v0.0.4 | 2/2 | Complete | 2026-06-09 |
| 15. Framework 死代码清理 | v0.0.5 | 1/1 | Complete    | 2026-06-10 |
| 16. Framework 安全修复 | v0.0.5 | 4/4 | Complete    | 2026-06-10 |
| 17. Framework 逻辑修复 | v0.0.5 | 4/4 | Complete    | 2026-06-10 |
| 18. Backend 全面修复 | v0.0.5 | 0/? | Not started | — |
| 19. Frontend 全面修复 | v0.0.5 | 0/? | Not started | — |
