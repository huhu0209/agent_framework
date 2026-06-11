# Phase 22: Simple Module Adapters — Skills, Hooks, Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 22-Simple Module Adapters — Skills, Hooks, Commands
**Areas discussed:** Skill 名称碰撞策略, Hook 合并语义, Command 发现范围, 加载失败容错策略

---

## Skill 名称碰撞策略

| Option | Description | Selected |
|--------|-------------|----------|
| 反转顺序 | from_loader() 入口反转 discover() 返回的 [global, project] 为 [project, global]，first-found wins 自然让 project 赢 | ✓ |
| last-found wins | 修改 SkillRegistry._full_refresh() 为 last-found wins，变更现有行为 | |
| 收集后覆盖+warning | 遍历全部目录收集后按名称分组，project 覆盖 global 并 emit warning | |

**User's choice:** 反转顺序（推荐）
**Notes:** 不改 SkillRegistry 内部逻辑，只在 from_loader() 入口处理

| Option | Description | Selected |
|--------|-------------|----------|
| 静默覆盖 | project 覆盖 global 时无日志输出，与现有行为一致 | ✓ |
| warning 日志 | 打印 warning 帮助发现意外覆盖 | |

**User's choice:** 静默覆盖（推荐）
**Notes:** 保持与现有 SkillRegistry 行为一致

---

## Hook 合并语义

| Option | Description | Selected |
|--------|-------------|----------|
| 按 event 追加合并 | 分别调用 load_from_json()，project hook 追加到 global 同 event 列表末尾 | ✓ |
| project 整体替换 | project hooks.json 完全替换 global，丢失全局默认 hook | |
| 按 event+matcher 替换 | 每个 event+matcher 组合由 project 完全替换 global 的同名组合 | |

**User's choice:** 按 event 追加合并（推荐）
**Notes:** 保留全局 hook 作为基础，项目 hook 作为增强

| Option | Description | Selected |
|--------|-------------|----------|
| global → project | 全局先加载先触发，项目后加载后触发 | ✓ |
| project → global | 项目先加载先触发 | |

**User's choice:** global → project（推荐）
**Notes:** 加载顺序 = 触发顺序，符合"全局为基础"的语义

---

## Command 发现范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅注入 SkillRegistry | from_loader() 创建 CommandDispatcher，内部调用 SkillRegistry.from_loader() 获取注册表后传入 | ✓ |
| 目录扫描加载命令文件 | 扫描 discover("commands") 目录加载 Python/JSON/YAML 命令文件 | |
| 注入 SR + JSON 命令定义 | 同时注入 SkillRegistry 和扫描 JSON 声明式命令定义 | |

**User's choice:** 仅注入 SkillRegistry（推荐）
**Notes:** 不引入新的命令文件格式。discover("commands") 目录预留未来扩展

---

## 加载失败容错策略

| Option | Description | Selected |
|--------|-------------|----------|
| warning 跳过 | 无效文件 warning 跳过继续加载，复用现有容错模式 | ✓ |
| raise 中断 | 文件解析失败时 raise 中断整个 from_loader() | |
| 混合策略 | Skill 无效时跳过，Hook JSON 无效时 raise | |

**User's choice:** warning 跳过（推荐）
**Notes:** 复用 SkillRegistry._parse_skill_document() 和 HookManager.load_from_json() 已有的容错逻辑，不在 from_loader() 层面增加额外容错

---

## Claude's Discretion

- from_loader() 实现方式（推荐 @classmethod）
- hooks.json 不存在时的行为（静默跳过）
- SkillRegistry.from_loader() 是否需 refresh()（构造函数内部已自动处理）
- HookManager.trusted 参数在 from_loader() 中的默认值
- 测试文件组织和测试用例设计
- 工厂方法代码放在现有模块文件内还是单独文件

## Deferred Ideas

None — discussion stayed within phase scope
