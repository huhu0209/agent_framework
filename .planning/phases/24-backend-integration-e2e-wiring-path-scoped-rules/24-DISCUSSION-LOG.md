# Phase 24: Backend Integration + E2E Wiring + Path-Scoped Rules - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 24-Backend Integration + E2E Wiring + Path-Scoped Rules
**Areas discussed:** Backend Config 统一, Rules 匹配语法, PromptAssembler 集成, AgentFactory 重构深度

---

## Backend Config 统一

| Option | Description | Selected |
|--------|-------------|----------|
| A: ConfigLoader 作为 fallback | Backend Settings 保留 BaseSettings + APP_ env，ConfigLoader 提供默认值 | ✓ |
| B: 替换为 ConfigLoader | 删除 backend Settings，统一用 ConfigLoader | |
| C: ConfigLoader → env 注入 | 启动时注入 os.environ，隐式依赖 | |
| You decide | 交给你判断 | |

**User's choice:** A: ConfigLoader 作为 fallback
**Notes:** 零破坏性变更，backend 和 framework 各自独立初始化。

| Option | Description | Selected |
|--------|-------------|----------|
| A: 并行初始化 | main.py lifespan 中独立创建 ConfigLoader 和 backend Settings | ✓ |
| B: Settings 内嵌 ConfigLoader | backend Settings.__init__ 内部创建 ConfigLoader | |

**User's choice:** A: 并行初始化

| Option | Description | Selected |
|--------|-------------|----------|
| A: redis_url 留 backend | 框架层不感知 Redis | ✓ |
| B: 提升到 framework Settings | 所有配置统一到一处 | |

**User's choice:** A: redis_url 留 backend

| Option | Description | Selected |
|--------|-------------|----------|
| A: 测试验证 | 写测试确保 config/ 不导入框架其他模块 | ✓ |
| B: 文档约束 | 在 config/__init__.py 加注释说明 | |

**User's choice:** A: 测试验证

---

## Rules 匹配语法

| Option | Description | Selected |
|--------|-------------|----------|
| A: Glob 模式 | fnmatch 库，支持 * 和 ** 通配符 | ✓ |
| B: 前缀匹配 | paths 前缀，简单但不够精确 | |
| C: 正则表达式 | 最灵活但复杂 | |

**User's choice:** A: Glob 模式

| Option | Description | Selected |
|--------|-------------|----------|
| A: 相对于项目根目录 | 与 ConfigLoader.project_dir 一致 | ✓ |
| B: 相对于 CWD | 更灵活但不同 CWD 行为不同 | |

**User's choice:** A: 相对于项目根目录

| Option | Description | Selected |
|--------|-------------|----------|
| A: 始终加载 | 无 paths 字段的 rules 全局生效 | ✓ |
| B: 不加载 | 所有规则必须显式声明 paths | |

**User's choice:** A: 始终加载

| Option | Description | Selected |
|--------|-------------|----------|
| A: 新 rules/ 模块 | 与 skills/, hooks/ 等平级 | ✓ |
| B: 放在 prompts/ 内 | 减少模块数量 | |
| You decide | 交给你判断 | |

**User's choice:** A: 新 rules/ 模块

---

## PromptAssembler 集成

| Option | Description | Selected |
|--------|-------------|----------|
| A: assemble(loader, profile) | 扩展签名，内部自动调用 loader | ✓ |
| B: 调用方手动拼装 | 调用方分别调用各 loader，手动传 assemble | |
| C: 新建 SystemPromptBuilder | 新类解耦但增加复杂度 | |

**User's choice:** A: assemble(loader, profile)

| Option | Description | Selected |
|--------|-------------|----------|
| A: 设计文档顺序 | user-provided → rules → soul → instructions → identity → skills → tool-guidance | ✓ |
| B: 保持现有顺序 | 最小改动 | |

**User's choice:** A: 设计文档顺序

| Option | Description | Selected |
|--------|-------------|----------|
| A: 新增 assemble_full() | 保留旧 API，新增方法 | |
| B: 修改 assemble() 签名 | 破坏性变更 | |
| You decide | 交给你判断 | |

**User's choice:** 不需要考虑向后兼容，还没开始做项目

| Option | Description | Selected |
|--------|-------------|----------|
| A: context_path 参数过滤 | assemble() 接受可选 context_path，传给 RuleLoader | ✓ |
| B: 始终加载全部 rules | 不支持路径条件匹配 | |

**User's choice:** A: context_path 参数过滤

---

## AgentFactory 重构深度

| Option | Description | Selected |
|--------|-------------|----------|
| A: 扩展现有 AgentFactory | 新增 from_configloader() 工厂方法 | ✓ |
| B: 新建编排层 | 新建 AgentOrchestrator 类 | |
| You decide | 交给你判断 | |

**User's choice:** A: 扩展现有 AgentFactory

| Option | Description | Selected |
|--------|-------------|----------|
| A: 单次调用全初始化 | from_configloader() 一次完成所有注册表初始化 | ✓ |
| B: 分步初始化 | 先 create_registries() 再 create_agent() | |

**User's choice:** A: 单次调用全初始化

| Option | Description | Selected |
|--------|-------------|----------|
| A: 集成测试验证 | 独立集成测试覆盖全链路 | ✓ |
| B: 分散验证 | 在各模块测试中分散验证 | |

**User's choice:** A: 集成测试验证

---

## Claude's Discretion

- from_configloader() 内部各 from_loader() 的调用顺序和错误处理策略
- RuleLoader 类的具体 API 设计
- rules/*.md 文件解析的 frontmatter 格式（复用 parse_frontmatter）
- 集成测试文件组织和测试用例设计
- 叶依赖测试的具体实现方式（AST 分析 vs import 尝试）
- PromptAssembler 新增块的 PromptBlock 属性值

## Deferred Ideas

None — discussion stayed within phase scope
