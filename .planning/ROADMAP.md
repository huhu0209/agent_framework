# Roadmap: Agent Framework

## Milestones

- ✅ **v0.0.1 彻底 Code Review** — Phases 1-5 (shipped 2026-05-29)
- ✅ **v0.0.2 Agent 扩展与编排** — Phases 6-8 (shipped 2026-05-29)
- ✅ **v0.0.3 Agent 可视化平台 MVP** — Phases 9-11 (shipped 2026-05-31)
- 🔵 **v0.0.4 全面代码审查** — Phases 12-14 (current)

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
| 12. Framework 代码审查 | v0.0.4 | 5/5 | Complete | 2026-06-09 | | — |
| 13. Backend 代码审查 | v0.0.4 | 2/2 | Complete | 2026-06-09 | | — |
| 14. Frontend 代码审查 | v0.0.4 | 2/2 | Complete | 2026-06-09 | | — |

---

## v0.0.4: 全面代码审查 (Phases 12-14)

**Goal:** 对三个模块进行系统性代码审查，找出死代码、逻辑漏洞、不合理设计和安全问题。

### Phase 12: Framework 代码审查

**Goal:** 全面审查 agent_framework/ 框架层代码质量

**Requirements:** FRMW-01, FRMW-02, FRMW-03, FRMW-04, FRMW-05

**Plans:** 5 plans

Plans:
- [x] 12-01-PLAN.md — ruff 自动扫描基线 + llm/ 模块人工审查
- [x] 12-02-PLAN.md — tools/ + agents/ 模块逐文件人工审查
- [x] 12-03-PLAN.md — memory/ + safety/ + teams/ + tasks/ 模块逐文件人工审查
- [x] 12-04-PLAN.md — orchestrator/ + a2a/ + skills/ + hooks/ + commands/ + prompts/ + transcript/ + viz/ 模块人工审查
- [x] 12-05-PLAN.md — 综合报告汇总 + 去重 + 质量检查 + 用户验证

**Scope:**
- 使用静态分析工具检测未使用的函数、类、import、变量
- 逐模块审查逻辑正确性、竞态条件、错误处理
- 审查设计模式合理性（过度工程、违反 SOLID、重复代码）
- 安全审查（注入、信息泄露、路径遍历、不安全默认值）
- 产出 REVIEW-FRAMEWORK.md（含 CRITICAL/HIGH/MEDIUM/LOW 分级）

**Success Criteria:**
1. REVIEW-FRAMEWORK.md 产出，覆盖所有审查维度
2. 所有 CRITICAL 和 HIGH 问题有明确修复建议
3. 死代码清单完整（含行号和删除风险评估）
4. 独立审查产出（per CONTEXT D-03），不逐项对照 v0.0.1 报告

---

### Phase 13: Backend 代码审查

**Goal:** 全面审查 backend/ 应用层代码质量

**Requirements:** BKND-01, BKND-02, BKND-03, BKND-04, BKND-05

**Plans:** 2 plans

Plans:
- [x] 13-01-PLAN.md — ruff 自动扫描 + 逐文件人工审查 + 数据流追踪
- [x] 13-02-PLAN.md — 跨层交叉参照 + 报告汇总 + 质量检查 + 用户验证

**Scope:**
- 使用静态分析工具检测未使用的函数、类、import、变量
- 审查 API 端点逻辑、数据验证、错误处理
- 审查服务层设计模式合理性
- 安全审查（SQL 注入、认证绕过、敏感信息泄露、CORS 配置）
- 产出 REVIEW-BACKEND.md（含 CRITICAL/HIGH/MEDIUM/LOW 分级）

**Success Criteria:**
1. REVIEW-BACKEND.md 产出，覆盖所有审查维度
2. API 端点安全审查完整（认证、授权、输入验证）
3. 数据流路径追踪完整（请求→服务→模型→响应）
4. 与框架层审查结果对照，标注跨层问题

---

### Phase 14: Frontend 代码审查

**Goal:** 全面审查 frontend/ 前端代码质量

**Requirements:** FRNT-01, FRNT-02, FRNT-03, FRNT-04, FRNT-05

**Plans:** 2 plans

Plans:
- [x] 14-01-PLAN.md — ESLint 自动扫描基线 + 全文件人工审查 + 审查汇总
- [x] 14-02-PLAN.md — 跨层交叉参照 + 质量检查 + 用户验证

**Scope:**
- 使用静态分析工具检测未使用的组件、函数、import、变量
- 审查 React 状态管理逻辑、副作用处理、错误边界
- 审查 PixiJS 渲染层设计合理性（内存泄漏、Ticker 管理、事件清理）
- 安全审查（XSS、敏感信息暴露、WebSocket 安全）
- 产出 REVIEW-FRONTEND.md（含 CRITICAL/HIGH/MEDIUM/LOW 分级）

**Success Criteria:**
1. REVIEW-FRONTEND.md 产出，覆盖所有审查维度
2. React 组件树完整审查（props drilling、re-render 问题、context 使用）
3. PixiJS 资源管理审查（Application 销毁、Ticker 清理、纹理释放）
4. WebSocket 客户端安全审查完整
