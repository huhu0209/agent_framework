# Phase 6: Agent 类型扩展 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 06-agent-types
**Areas discussed:** AgentEvent.data 结构设计, PlanAndSolve 上下文与偏离检测, Reflection 评估标准与 verdict, ABC 提取策略与兼容边界

---

## AgentEvent.data 结构设计

| Option | Description | Selected |
|--------|-------------|----------|
| 精简模式 | data 只带必要字段（step→text+tool_calls 等） | ✓ |
| 丰富模式 | data 带完整信息（usage、model、thinking 等） | |
| 按需扩展 | 基础字段固定，扩展字段通过可选 key 动态包含 | |

**User's choice:** 精简模式

| Option | Description | Selected |
|--------|-------------|----------|
| 双层事件 | 保留 LoopEvent 不变，AgentEvent 是新独立类型 | |
| 统一事件 | AgentEvent 替代 LoopEvent | |
| 继承关系 | AgentEvent 基类，LoopEvent 继承并加 plan | ✓ |

**User's choice:** 继承关系
**Notes:** 用户详细分析了影响面：AgentEvent 基类 → LoopEvent 继承并加 plan。Python 协变返回类型保证兼容。仅 sub_agent/runner/manager 标注需更新。59 个测试零改动。用户强调 plan 不应该塞进 data dict 丢掉类型安全。

| Option | Description | Selected |
|--------|-------------|----------|
| 按描述固定 | step→text+tool_calls; done→text; error→message 等 | ✓ |
| 自定义 | 用户有具体想法要补充 | |

**User's choice:** 按描述固定

---

## PlanAndSolve 上下文与偏离检测

| Option | Description | Selected |
|--------|-------------|----------|
| 仅步骤描述 | 每步只拿步骤描述 + 原始任务 | |
| 步骤描述 + 前序摘要 | 每步拿步骤描述 + 原始任务 + 前序步骤摘要输出 | ✓ |
| 累积全部前序输出 | 每步拿步骤描述 + 原始任务 + 全部前序完整输出 | |

**User's choice:** 步骤描述 + 前序摘要

| Option | Description | Selected |
|--------|-------------|----------|
| LLM 评估偏离 | 每步执行后让 LLM 判断是否偏离 | |
| 规则判断偏离 | 基于规则：error 结果、空输出等 | |
| 混合策略 | 先规则检查，无法判断时 fallback 到 LLM 评估 | ✓ |

**User's choice:** 混合策略

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有 planner | 复用 PlanningState + parse_plan_response() | ✓ |
| 独立计划状态 | PlanAndSolve 自己管理计划状态 | |

**User's choice:** 复用现有 planner

---

## Reflection 评估标准与 verdict

| Option | Description | Selected |
|--------|-------------|----------|
| 三维度评估 | 正确性、完整性、清晰度 | ✓ |
| 二元判断 | 只判断满意/不满意 | |
| 可配置评估维度 | 通过构造参数传入自定义维度 | |

**User's choice:** 三维度评估

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic 模型 | dataclass + from_llm_response 容错 | ✓ |
| JSON 文本解析 | 纯文本 JSON 解析 | |
| Tool calling 结构化 | 定义 assessment 工具让 LLM 调用 | |

**User's choice:** dataclass + from_llm_response 容错
**Notes:** 用户强调不用 tool calling — Reflection 的评估是独立 completion（不是 AgentLoop 内部），加 tool definition 会变成 tool_use 往返增加复杂度。JSON 解析失败时 fallback satisfied=False。

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 AgentLoop | 执行和改进阶段都用 AgentLoop 实例 | ✓ |
| 纯 completion 调用 | 全程用独立 completion，不用 AgentLoop | |

**User's choice:** 复用 AgentLoop

---

## ABC 提取策略与兼容边界

| Option | Description | Selected |
|--------|-------------|----------|
| ABC 抽象基类 | Agent 是 ABC，定义抽象方法 run() | ✓ |
| Protocol 接口 | Agent 是 Protocol（结构化子类型） | |
| 普通基类 | Agent 是普通基类，run() raise NotImplementedError | |

**User's choice:** ABC 抽象基类

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 run() | 最小接口，只定义 run() 抽象方法 | ✓ |
| run() + name + description | 加 name/description 属性 | |
| 丰富接口 | run() + name + description + stop() + status 等 | |

**User's choice:** 仅 run()
**Notes:** AGENT-02 说不约束 init 签名。name/description 留到 Phase 8 A2A 协议时再考虑。

| Option | Description | Selected |
|--------|-------------|----------|
| 最小改动 | 只改 base.py/agent_loop.py/标注文件 | |
| 最小改动 + 导出更新 | 加上 __init__.py 导出更新和契约验证测试 | ✓ |

**User's choice:** 最小改动 + 导出更新

---

## Claude's Discretion

- PlanAndSolve 的 LLM 评估偏离的具体 prompt 设计
- Reflection 三维度评估的具体 prompt 设计
- 前序步骤摘要的生成方式（LLM 摘要 vs. 截取最后 N 字符）

## Deferred Ideas

None — discussion stayed within phase scope
