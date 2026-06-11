# Phase 21: Discovery + Loader + AGENTS.md Chain - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 21-Discovery + Loader + AGENTS.md Chain
**Areas discussed:** ConfigLoader 接口设计, AGENTS.md 链加载细节, Profile 加载策略, discover_paths 路径解析

---

## ConfigLoader 接口设计

| Question | Options | Selected |
|----------|---------|----------|
| load_settings() 缓存策略 | 无缓存每次重新加载 / ConfigLoader 内部缓存 / 外部单例管理 | ✓ 无缓存 |
| discover() 返回类型 | 纯 list[Path] / 带元组的 list[tuple[Path, str]] | ✓ 纯 list[Path] |
| settings.local.json 路径 | 自动尝试读取 / 构造时传入 project_dir | ✓ 自动尝试读取 |
| 构造函数参数 | 零参数构造 / 可配置目录参数 / 带默认值的可选参数 | ✓ 带默认值的可选参数（D-04 修订） |

**User's choice:** 全部选择推荐项。构造函数在讨论 discover_paths 测试策略时修订为带默认值的可选参数。
**Notes:** 零参数构造和 tmp_path 测试有张力，通过带默认值的可选参数调和。

---

## AGENTS.md 链加载细节

| Question | Options | Selected |
|----------|---------|----------|
| 父目录链终止条件 | 仅 .git/ / 多 VCS 标记 / 无边界到根目录 | ✓ 仅 .git/ |
| 遍历方向 | 从 .git/ 根到 CWD / 先向上收集再反转 | ✓ 从 .git/ 根到 CWD |
| 文件缺失处理 | 静默跳过 / 跳过但 debug 日志 | ✓ 静默跳过 |
| 拼接分隔符 | 双换行 / --- 分隔线 / Markdown 标题标注来源 | ✓ Markdown 标题标注来源 |
| 来源标注格式 | HTML 注释 / Markdown 标题 / 不标注 | ✓ `# Source: <path>` 标题格式 |

**User's choice:** 用户主动要求标注来源，选择了 Markdown 标题格式。
**Notes:** 用户原话："需要备注来源 比如说 ---.agent/AGENT.md --- 或者说 <.agent/AGENT.md>"。最终选择了 `# Source: <path>` 格式。

---

## Profile 加载策略

| Question | Options | Selected |
|----------|---------|----------|
| Profile 名称来源 | 调用方显式传入 / 从 settings.json 读取 / 两者都支持 | ✓ 调用方显式传入 |
| 同名 profile 冲突 | 先加载 global 后 project 覆盖 / 只加载 project | ✓ 先 global 后 project 覆盖 |
| 缺失子文件处理 | 跳过字段留空 / 全部缺失时 warning | ✓ 跳过字段留空 |

**User's choice:** 全部选择推荐项。不修改 Settings 模型，复用已有 _read_file() 逻辑。
**Notes:** Profile 合并按字段独立（soul.md / agents.md / identity.md / tool_guidance.md 各自独立覆盖）。

---

## discover_paths 路径解析

| Question | Options | Selected |
|----------|---------|----------|
| 模块映射维护 | 硬编码映射表 / 直接用 module_name | ✓ 硬编码映射表 |
| 路径缺失处理 | 静默跳过 / 缺失时 debug 日志 | ✓ 静默跳过 |
| 测试策略 | tmp_path 构建 mock 目录 / monkeypatch Path.home/cwd | ✓ tmp_path mock |
| 构造函数调和 | 带默认值的可选参数 / 纯零参数 + monkeypatch | ✓ 带默认值的可选参数 |

**User's choice:** 全部选择推荐项。确认 ConfigLoader(global_dir=, project_dir=) 带默认值的方案。
**Notes:** 这一轮讨论揭示了 D-04 需要修订，已更新。

---

## Claude's Discretion

- 具体的 MODULE_DIRS 映射表内容
- load_settings() JSON 解析错误的 error handling 策略
- load_agents_md() 返回类型和空结果处理
- discover_paths() 对未知 module_name 的验证策略
- 测试文件组织和测试用例设计
- 新增文件的命名（loader.py / discovery.py / instructions.py 等）

## Deferred Ideas

None — discussion stayed within phase scope
