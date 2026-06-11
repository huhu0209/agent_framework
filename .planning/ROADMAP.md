# Roadmap: Agent Framework

## Milestones

- ✅ **v0.0.1 彻底 Code Review** — Phases 1-5 (shipped 2026-05-29)
- ✅ **v0.0.2 Agent 扩展与编排** — Phases 6-8 (shipped 2026-05-29)
- ✅ **v0.0.3 Agent 可视化平台 MVP** — Phases 9-11 (shipped 2026-05-31)
- ✅ **v0.0.4 全面代码审查** — Phases 12-14 (shipped 2026-06-09)
- ✅ **v0.0.5 Review 问题修复** — Phases 15-19 (shipped 2026-06-10)
- 🚧 **v0.0.6 路径文件的统一** — Phases 20-24 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

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
<summary>✅ v0.0.5 Review 问题修复 (Phases 15-19) — SHIPPED 2026-06-10</summary>

- [x] Phase 15: Framework 死代码清理 (1/1 plans) — completed 2026-06-10
- [x] Phase 16: Framework 安全修复 (4/4 plans) — completed 2026-06-10
- [x] Phase 17: Framework 逻辑修复 (4/4 plans) — completed 2026-06-10
- [x] Phase 18: Backend 全面修复 (3/3 plans) — completed 2026-06-10
- [x] Phase 19: Frontend 全面修复 (2/2 plans) — completed 2026-06-10

</details>

### 🚧 v0.0.6 路径文件的统一 (In Progress)

**Milestone Goal:** 参照 Claude Code 路径机制，实现统一配置层级体系和模块自动发现

- [x] **Phase 20: Config Foundation — Settings Model + Merge Engine** - 构建 Settings Pydantic 模型和类型感知合并函数 (completed 2026-06-11)
- [x] **Phase 21: Discovery + Loader + AGENTS.md Chain** - 完成路径发现、ConfigLoader 入口类和指令链加载 (completed 2026-06-11)
- [ ] **Phase 22: Simple Module Adapters — Skills, Hooks, Commands** - 为已有 list[Path] 构造函数的模块添加 from_loader() 工厂方法
- [ ] **Phase 23: Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions** - 多目录扫描、名称冲突处理、复杂配置合并
- [ ] **Phase 24: Backend Integration + E2E Wiring + Path-Scoped Rules** - 应用层集成、端到端验证、零回归确认

## Phase Details

### Phase 20: Config Foundation — Settings Model + Merge Engine
**Goal**: 合并引擎和 Settings 模型就绪，可被后续所有阶段依赖
**Depends on**: Nothing (first phase of v0.0.6, pure new code)
**Requirements**: CFG-02, CFG-03, CFG-06
**Success Criteria** (what must be TRUE):
  1. _merge_settings() handles three strategies correctly: scalar override takes highest-priority value, dict shallow-merges keys, array produces union with dedup and order preserved
  2. Settings Pydantic model instantiates with all-default values when no config files exist (fresh-install safe)
  3. APP_* environment variables override scalar Settings fields at validation time using env_nested_delimiter='__'
  4. All 1002 existing tests pass unchanged after this phase
**Plans**: 2 plans

Plans:
- [x] 20-01: Settings model + merge engine

### Phase 21: Discovery + Loader + AGENTS.md Chain
**Goal**: ConfigLoader 作为完整可用的统一入口，支持路径发现和指令链加载
**Depends on**: Phase 20
**Requirements**: CFG-01, CFG-04, CFG-05, INS-01, INS-02, INS-04, INS-05
**Success Criteria** (what must be TRUE):
  1. ConfigLoader.load_settings() returns a merged Settings object by reading global → project → local → env in priority order
  2. discover_paths(module_name) returns ordered [global_path, project_path] for any of the 8 supported module types, gracefully handling missing directories
  3. load_agents_md() concatenates the full instruction chain: global AGENTS.md → project AGENTS.md → local AGENTS.md → parent directory traversal (stopping at .git boundary) → user.md
  4. Profile loading reads profiles/<name>/ directory files (soul.md, agents.md, identity.md, tool_guidance.md) from discovered paths
  5. All 1002 existing tests pass unchanged after this phase
**Plans**: 2 plans

Plans:
- [x] 21-01: discover_paths() + ConfigLoader core
- [x] 21-02: AGENTS.md chain loader + Profile loading

### Phase 22: Simple Module Adapters — Skills, Hooks, Commands
**Goal**: Skills、Hooks、Commands 模块可通过 from_loader() 工厂方法从 ConfigLoader 初始化
**Depends on**: Phase 21
**Requirements**: ADP-01, ADP-02, ADP-03, ADP-09
**Success Criteria** (what must be TRUE):
  1. SkillRegistry.from_loader(loader) creates a registry populated from discover("skills") paths, with project-level items overriding global same-name items
  2. HookManager.from_loader(loader) loads and merges hooks from all discovered hooks.json files
  3. CommandRegistry.from_loader(loader) loads commands from all discovered command directories
  4. All existing constructor signatures remain unchanged — from_loader() is purely additive
  5. All 1002 existing tests pass unchanged after this phase
**Plans**: 2 plans

Plans:
- [ ] 22-01: Simple adapters (Skills, Hooks, Commands from_loader)

### Phase 23: Complex Module Adapters — Agents, Profiles, MCP, Tasks, Permissions
**Goal**: 所有剩余模块适配器完成，支持多目录扫描和名称冲突处理
**Depends on**: Phase 22 (validates adapter pattern on simpler modules first)
**Requirements**: ADP-04, ADP-05, ADP-06, ADP-07, ADP-08
**Success Criteria** (what must be TRUE):
  1. AgentProfile.from_loader() loads agents from multi-directory scan with project overriding global and emitting warnings on name collisions
  2. AgentProfile.from_profile() discovers and loads a named profile across global and project scopes
  3. McpManager.from_loader() merges MCP server configs from all discovered paths
  4. TaskManager defaults tasks_dir to .agent-framework/tasks/
  5. PermissionPipeline receives allow/deny lists from Settings.permissions automatically
**Plans**: 2 plans

Plans:
- [ ] 23-01: Agents and Profiles adapters
- [ ] 23-02: MCP, Tasks, Permissions adapters

### Phase 24: Backend Integration + E2E Wiring + Path-Scoped Rules
**Goal**: 应用层完整集成，端到端链路验证通过，零回归
**Depends on**: Phase 23
**Requirements**: INS-03, INS-06, INT-01, INT-02, INT-03, INT-04, INT-05, INT-06
**Success Criteria** (what must be TRUE):
  1. backend/app/config/ derives default values from ConfigLoader.load_settings() without circular imports
  2. Backend AgentFactory initializes module registries via ConfigLoader in a single startup flow
  3. rules/*.md files support frontmatter paths conditions for scoped loading (path-scoped rules)
  4. PromptAssembler integrates the full instruction chain into the <user-provided> block and Profile files into corresponding tags
  5. Full end-to-end test: ConfigLoader loads settings → discovers modules → adapters create registries → all 1002+ existing tests pass
**Plans**: 2 plans

Plans:
- [ ] 24-01: Backend integration + config leaf dependency
- [ ] 24-02: E2E wiring + PromptAssembler integration
- [ ] 24-03: Path-scoped rules + zero-regression verification

## Progress

**Execution Order:**
Phases execute in numeric order: 20 → 21 → 22 → 23 → 24

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
| 15. Framework 死代码清理 | v0.0.5 | 1/1 | Complete | 2026-06-10 |
| 16. Framework 安全修复 | v0.0.5 | 4/4 | Complete | 2026-06-10 |
| 17. Framework 逻辑修复 | v0.0.5 | 4/4 | Complete | 2026-06-10 |
| 18. Backend 全面修复 | v0.0.5 | 3/3 | Complete | 2026-06-10 |
| 19. Frontend 全面修复 | v0.0.5 | 2/2 | Complete | 2026-06-10 |
| 20. Settings + Merge | v0.0.6 | 1/1 | Complete    | 2026-06-11 |
| 21. Discovery + Loader | v0.0.6 | 2/2 | Complete    | 2026-06-11 |
| 22. Simple Adapters | v0.0.6 | 0/? | Not started | - |
| 23. Complex Adapters | v0.0.6 | 0/? | Not started | - |
| 24. Integration + E2E | v0.0.6 | 0/? | Not started | - |
