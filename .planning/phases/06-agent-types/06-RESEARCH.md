# Phase 6: Agent 类型扩展 - Research

**Researched:** 2026-05-29
**Domain:** Agent 抽象层 + Plan-and-Solve Agent + Reflection Agent
**Confidence:** HIGH

## Summary

Phase 6 在现有 `AgentLoop`（ReAct 循环）基础上建立三层扩展：(1) `Agent` ABC + `AgentEvent` 基础设施，(2) `PlanAndSolveAgent` 先规划后执行模式，(3) `ReflectionAgent` 执行-反省-改进循环。核心设计决策已在 CONTEXT.md 中锁定，所有模式均已在代码库中验证可行。

现有代码库提供了丰富的可复用资产：`PlanningState` + `parse_plan_response()` 用于计划解析和偏离检测，`AgentLoop` 作为成熟的 ReAct 执行引擎，`create_filtered_router()` 用于工具过滤。ABC 继承模式和 AsyncGenerator 协变返回类型已在 Python 3.11 环境中验证通过。

**Primary recommendation:** 严格按 06-01 -> 06-02/06-03 顺序构建。06-01 是零破坏性改动（仅添加基类和类型标注），06-02 和 06-03 各自独立创建新文件，互不依赖。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** AgentEvent 为基类（dataclass），字段：`type: str`, `step: int`, `data: dict[str, Any]`。LoopEvent 继承 AgentEvent 并增加 `plan: PlanSnapshot | None = None`
- **D-02:** AgentEvent.data 精简模式，各类型只带必要字段
- **D-03:** 仅 sub_agent.py、tasks/runner.py、teams/manager.py 的类型标注从 `AgentLoop` 更新为 `Agent`。59 个测试文件零改动
- **D-04:** 每个步骤的 AgentLoop 实例接收：原始任务 + 步骤描述 + 前序步骤的摘要输出
- **D-05:** 偏离检测使用混合策略：规则检查 + LLM fallback。replan 硬上限 2 次
- **D-06:** 复用现有 `orchestrator/planner.py` 的 `PlanningState` + `parse_plan_response()`
- **D-07:** 空计划时 fallback 到直接 ReAct 执行
- **D-08:** 评估基于三维度：正确性、完整性、清晰度。每个维度 1-5 分
- **D-09:** ReflectionVerdict 为 dataclass，提供 `from_llm_response()` classmethod 容错解析
- **D-10:** 执行和改进阶段复用 AgentLoop，仅反射/评估阶段用独立 LLM completion
- **D-11:** 改进轮次硬上限 2 次，不满意时将 critique 注入下一轮用户消息
- **D-12:** Agent 为 ABC，仅定义 `run() -> AsyncGenerator[AgentEvent, None]`。不约束 `__init__`
- **D-13:** 文件改动范围：agents/base.py、agents/agent_loop.py、agents/sub_agent.py、tasks/runner.py、teams/manager.py、agents/__init__.py

### Claude's Discretion
- PlanAndSolve 的 LLM 评估偏离的具体 prompt 设计
- Reflection 三维度评估的具体 prompt 设计
- 前序步骤摘要的生成方式（LLM 摘要 vs. 截取最后 N 字符）

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-01 | AgentEvent 统一事件模型（type, step, data dict） | dataclass 模式 + 现有 LoopEvent 字段分析 |
| AGENT-02 | Agent ABC 定义 `run() -> AsyncGenerator[AgentEvent, None]` | Python ABC + 协变返回类型验证通过 |
| AGENT-03 | AgentLoop 实现 Agent 接口，LoopEvent 继承 AgentEvent | 继承方向 + 协变性已验证 |
| AGENT-04 | sub_agent.py/runner.py/manager.py 类型标注更新为 Agent | 3 个文件各 1 处 import + 类型标注 |
| AGENT-05 | 现有 687 测试全部通过 | 无破坏性改动：仅添加基类 + 更新标注 |
| PLAN-01 | PlanAndSolveAgent(Agent) 先规划后执行 | 复用 PlanningState + 每步独立 AgentLoop |
| PLAN-02 | 生成计划阶段调用 LLM 产出有序步骤列表 | 复用 parse_plan_response() |
| PLAN-03 | 每个步骤用独立 AgentLoop 实例，步骤间不累积 context | create_filtered_router() 模式 |
| PLAN-04 | 偏离检测 + 重新规划，replan 硬上限 2 次 | 规则检查 + LLM fallback 混合策略 |
| PLAN-05 | 空计划时 fallback 到直接 ReAct 执行 | 降级为 AgentLoop 实例 |
| REFL-01 | ReflectionAgent(Agent) 执行-反省-改进循环 | 三阶段循环 + 硬上限 |
| REFL-02 | 反省阶段让 LLM 评估输出质量，结构化 verdict | ReflectionVerdict dataclass + JSON 解析 |
| REFL-03 | 改进轮次硬上限 2 次 | 循环计数器 + 硬编码上限 |
| REFL-04 | 不满意时将 critique 注入下一轮用户消息 | UserMessage 构造 + 提示模板 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Agent ABC + AgentEvent 定义 | Framework Core (agents/) | — | 统一接口契约，所有 Agent 类型的基类 |
| AgentLoop 继承 Agent | Framework Core (agents/) | — | 现有 ReAct 循环适配新接口 |
| 类型标注更新 (3 个文件) | Framework Core | — | 从具体类型改为抽象类型，面向接口编程 |
| PlanAndSolve 计划生成 | Framework Core (agents/) | LLM Adapter | LLM 调用产出步骤列表 |
| PlanAndSolve 步骤执行 | Framework Core (agents/) | AgentLoop | 复用 AgentLoop 做实际执行 |
| PlanAndSolve 偏离检测 | Framework Core (agents/) | LLM Adapter | 规则检查为主，LLM 为辅 |
| Reflection 评估 | Framework Core (agents/) | LLM Adapter | 独立 LLM completion 调用 |
| Reflection 执行/改进 | Framework Core (agents/) | AgentLoop | 复用 AgentLoop 做实际执行 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python abc | 3.11 stdlib | ABC + @abstractmethod | 标准库，Agent 基类定义 [VERIFIED: 代码库验证] |
| Python dataclasses | 3.11 stdlib | AgentEvent, LoopEvent, ReflectionVerdict | 与现有 LoopEvent/PlanItem/PlanSnapshot 一致 [VERIFIED: 代码库验证] |
| Python typing.AsyncGenerator | 3.11 stdlib | Agent.run() 返回类型 | 与现有 AgentLoop.run() 一致 [VERIFIED: 代码库验证] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| agent_framework.orchestrator.planner | 内部 | PlanningState + parse_plan_response | PlanAndSolve 计划解析和偏离检测 |
| agent_framework.agents.sub_agent.create_filtered_router | 内部 | 工具过滤 | PlanAndSolve 每步创建受限 AgentLoop |
| agent_framework.llm.types | 内部 | Message, CompletionConfig, CompletionResult | LLM completion 调用（Reflection 评估） |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| abc.ABC + @abstractmethod | typing.Protocol (structural) | Protocol 更宽松但不强制子类关系。决策已锁定用 ABC (D-12) |
| dataclass | Pydantic BaseModel | 现有 LoopEvent 用 dataclass，保持一致。决策已锁定 (D-01) |

**Installation:** 无新外部依赖。所有实现基于现有标准库和内部模块。

## Package Legitimacy Audit

此阶段不安装任何外部包，所有实现基于 Python 标准库和项目内部模块。

**Packages removed due to slopcheck [SLOP] verdict:** none (no external packages)
**Packages flagged as suspicious [SUS]:** none (no external packages)

## Architecture Patterns

### System Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────┐
│                      agents/base.py                         │
│  ┌─────────────┐    ┌──────────────┐                        │
│  │ AgentEvent   │    │ Agent (ABC)  │                        │
│  │ (dataclass)  │    │ run()        │                        │
│  └──────┬───────┘    └──────┬───────┘                        │
│         │                   │                                │
├─────────┼───────────────────┼────────────────────────────────┤
│         ▼                   ▼                                │
│  agents/agent_loop.py                                       │
│  ┌─────────────┐    ┌──────────────┐                        │
│  │ LoopEvent    │    │ AgentLoop    │                        │
│  │(AgentEvent)  │    │ (Agent)      │                        │
│  └─────────────┘    └──────────────┘                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  agents/plan_and_solve.py (NEW)                             │
│  ┌────────────────────────────────┐                         │
│  │ PlanAndSolveAgent (Agent)      │                         │
│  │                                │                         │
│  │ 1. plan: LLM → [PlanItem]      │──── parse_plan_response │
│  │ 2. execute: each step → AgentLoop │── create_filtered_router│
│  │ 3. detect: rule + LLM drift    │──── PlanningState       │
│  │ 4. replan: max 2x              │                         │
│  │ 5. fallback: AgentLoop if no plan│                       │
│  └────────────────────────────────┘                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  agents/reflection.py (NEW)                                 │
│  ┌────────────────────────────────┐                         │
│  │ ReflectionAgent (Agent)        │                         │
│  │                                │                         │
│  │ 1. execute: AgentLoop → output │                         │
│  │ 2. reflect: LLM → Verdict      │──── ReflectionVerdict   │
│  │ 3. improve: if not satisfied,  │                         │
│  │    inject critique → AgentLoop │                         │
│  │ 4. repeat: max 2 improvements  │                         │
│  └────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```text
framework/agent_framework/agents/
├── __init__.py              # 更新导出：Agent, AgentEvent
├── base.py                  # Agent ABC + AgentEvent dataclass（从空文件变为实现）
├── agent_loop.py            # LoopEvent 继承 AgentEvent，AgentLoop 继承 Agent
├── sub_agent.py             # import 类型标注 AgentLoop → Agent
├── plan_and_solve.py        # 新建：PlanAndSolveAgent
└── reflection.py            # 新建：ReflectionAgent + ReflectionVerdict
```

### Pattern 1: Agent ABC + 协变返回类型
**What:** Agent ABC 定义统一接口，子类通过 Python 协变返回类型提供更具体的事件类型。
**When to use:** 所有 Agent 类型实现。
**Example:**
```python
# agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

@dataclass
class AgentEvent:
    """Agent 事件基类。"""
    type: str  # "step" | "tool_result" | "done" | "max_steps" | "error"
    step: int
    data: dict[str, Any] = field(default_factory=dict)

class Agent(ABC):
    """Agent 抽象基类，定义统一运行接口。"""
    @abstractmethod
    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        yield  # pragma: no cover
```

```python
# agents/agent_loop.py (修改)
@dataclass
class LoopEvent(AgentEvent):
    """Agent Loop 每一步产生的事件。"""
    plan: PlanSnapshot | None = None

class AgentLoop(Agent):
    async def run(self, user_message: str, ...) -> AsyncGenerator[LoopEvent, None]:
        # LoopEvent 是 AgentEvent 的子类，Python 协变返回类型保证兼容
        ...
```

### Pattern 2: PlanAndSolve 先规划后执行
**What:** 将复杂任务分解为有序步骤，每步独立执行并检测偏离。
**When to use:** 复杂任务需要结构化执行路径时。
**Example:**
```python
# agents/plan_and_solve.py (新建)
class PlanAndSolveAgent(Agent):
    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        max_steps_per_plan_item: int = 10,
        max_replans: int = 2,
    ) -> None: ...

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        # 1. 生成计划
        plan_items = await self._generate_plan(user_message)
        if not plan_items:
            # D-07: fallback 到 ReAct
            async for event in self._run_react(user_message):
                yield event
            return

        # 2. 逐步执行
        replan_count = 0
        step_outputs: list[str] = []
        for item in plan_items:
            step_prompt = self._build_step_prompt(user_message, item, step_outputs)
            result = await self._execute_step(step_prompt)
            step_outputs.append(result)

            # 3. 偏离检测
            if self._detect_drift(result):
                if replan_count < self.max_replans:
                    replan_count += 1
                    plan_items = await self._replan(...)
                else:
                    yield AgentEvent(type="error", ...)
                    return

        # 4. 完成
        yield AgentEvent(type="done", step=..., data={"text": final_output})
```

### Pattern 3: Reflection 执行-反省-改进循环
**What:** 执行任务后自评输出质量，不满意则改进，形成闭环。
**When to use:** 需要高质量输出的任务。
**Example:**
```python
# agents/reflection.py (新建)
@dataclass
class ReflectionVerdict:
    """反省评估结论。"""
    satisfied: bool
    scores: dict[str, int]
    critique: str

    @classmethod
    def from_llm_response(cls, text: str) -> ReflectionVerdict:
        try:
            data = json.loads(text)
            return cls(
                satisfied=data.get("satisfied", False),
                scores=data.get("scores", {}),
                critique=data.get("critique", ""),
            )
        except (json.JSONDecodeError, AttributeError):
            return cls(
                satisfied=False,
                scores={},
                critique=f"评估失败，原始输出：{text[:200]}",
            )

class ReflectionAgent(Agent):
    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        current_prompt = user_message
        for improvement_round in range(3):  # 1 执行 + 2 改进
            # 执行阶段
            output = await self._execute(current_prompt)
            yield AgentEvent(type="step", ...)

            # 评估阶段（独立 LLM 调用）
            verdict = await self._reflect(user_message, output)

            if verdict.satisfied:
                yield AgentEvent(type="done", ...)
                return

            # 改进阶段：注入 critique
            current_prompt = f"{user_message}\n\n[评估反馈]\n{verdict.critique}\n\n请根据以上反馈改进。"

        yield AgentEvent(type="done", ...)  # 达到上限，返回最终输出
```

### Anti-Patterns to Avoid
- **在 Agent ABC 上定义 `__init__` 签名：** D-12 明确不约束 `__init__`，各 Agent 类型构造参数差异大（AgentLoop 15 参数 vs PlanAndSolve 6 参数），强行统一会阻碍扩展
- **在 AgentEvent.data 中存储完整对象：** D-02 锁定精简模式，只带必要字段（字符串、bool、简单 dict），不传 PlanSnapshot 或 CompletionResult 等大对象
- **Reflection 评估使用 tool calling：** D-10 明确仅用独立 LLM completion，避免将简单评估变为 tool_use 往返增加延迟和复杂度
- **在测试文件中 import Agent 或 AgentEvent：** D-03 要求 59 个测试文件零改动。测试文件继续 import LoopEvent，因为 LoopEvent 继承 AgentEvent 所以接口兼容
- **PlanAndSolve 步骤间累积完整 context：** D-04 明确只用摘要输出，不是完整历史。累积 context 会耗尽 token 预算

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 计划解析 | 自定义 XML/JSON 解析器 | parse_plan_response() | 已有 `<plan>` 标签解析 + 多行支持 + 空计划处理 |
| 偏离检测 | 自定义 drift 逻辑 | PlanningState.check_drift() | 已有 warn/abort 阈值 + 状态转换验证 |
| 工具过滤 | 手动构建白名单 router | create_filtered_router() | 已有递归工具排除（run_subagent, task_create, spawn_teammate） |
| LLM 调用 | 直接 HTTP 请求 | ILLMAdapter.complete() | 已有重试、断路器、provider 抽象 |
| JSON 解析 + 容错 | 手写解析器 | json.loads() + try/except + 默认值 | D-09 容错模式，解析失败返回默认 verdict |

**Key insight:** 此阶段是组合现有组件构建新模式，而非从零实现。PlanningState、AgentLoop、create_filtered_router、ILLMAdapter 都是经过 687 测试验证的成熟组件。

## Common Pitfalls

### Pitfall 1: LoopEvent 继承顺序导致字段默认值冲突
**What goes wrong:** AgentEvent 的 `data` 有 `field(default_factory=dict)`，LoopEvent 继承后新增 `plan: PlanSnapshot | None = None`。如果 LoopEvent 字段顺序不对（非默认字段在默认字段之前），dataclass 会报错。
**Why it happens:** Python dataclass 要求有默认值的字段必须在无默认值字段之后，继承时同样适用。
**How to avoid:** 确保 AgentEvent 所有字段都有默认值（`type` 和 `step` 无默认值，`data` 有），LoopEvent 新增的 `plan` 字段放在最后且有默认值 `None`。当前 LoopEvent 已是此结构，改动安全。
**Warning signs:** `TypeError: non-default argument follows default argument`

### Pitfall 2: AgentLoop 继承 Agent 后 run() 签名不匹配
**What goes wrong:** Agent ABC 定义 `run(self, user_message: str)`，但 AgentLoop.run() 有额外参数 `plan: list[PlanItem] | None = None` 和 `resume: bool = False`。
**Why it happens:** 子类方法签名必须兼容父类。Python 允许子类添加额外可选参数（keyword-only），但类型检查器可能警告。
**How to avoid:** 确保额外参数都是 keyword-only（`*, plan=..., resume=...`）。当前 AgentLoop.run() 中 `plan` 不是 keyword-only，但 D-12 不约束 `__init__`，同理不约束 `run()` 的额外参数——ABC 只定义最低接口。实际验证：Python 运行时不检查签名匹配，`abstractmethod` 只检查方法是否存在。
**Warning signs:** mypy/pyright 可能报 `Signature incompatible with supertype`

### Pitfall 3: PlanAndSolve 步骤摘要丢失关键信息
**What goes wrong:** 前序步骤只传摘要，如果摘要质量差（截断关键信息），后续步骤无法正确衔接。
**Why it happens:** Claude's Discretion 区域，摘要方式未锁定。LLM 摘要成本高但质量好，截取最后 N 字符成本低但可能截断。
**How to avoid:** 推荐用截取最后 2000 字符作为初始实现（简单、零额外 LLM 调用），后续可升级为 LLM 摘要。每步输出通常不超过 2000 字符，截取即是完整输出。
**Warning signs:** 后续步骤输出质量明显低于单步执行

### Pitfall 4: Reflection 评估 JSON 解析失败导致 crash
**What goes wrong:** LLM 返回的 verdict JSON 可能格式错误、包含额外文本、或完全不是 JSON。
**Why it happens:** LLM 输出不可控，即使 prompt 要求 JSON 格式也不保证。
**How to avoid:** D-09 的容错模式已处理：`json.JSONDecodeError` 时返回 `satisfied=False, scores={}, critique=f"评估失败，原始输出：{text[:200]}"`。必须测试此路径。
**Warning signs:** 任何 `json.loads()` 调用没有 try/except 包裹

### Pitfall 5: 类型标注更新引入循环 import
**What goes wrong:** `sub_agent.py` / `runner.py` / `manager.py` 从 `agents.base` import `Agent`，如果 `base.py` 反向引用这些模块则产生循环。
**Why it happens:** 模块间依赖方向错误。
**How to avoid:** `agents/base.py` 只定义 ABC 和 dataclass，不 import 任何具体实现。确保依赖方向是单向的：`base.py` <- `agent_loop.py` <- `sub_agent.py` / `plan_and_solve.py` / `reflection.py`。runner.py 和 manager.py 从 `agents.base` import `Agent`，不会引入循环。
**Warning signs:** `ImportError` 或运行时 `AttributeError: partially initialized module`

## Code Examples

### AgentEvent + LoopEvent 继承（已验证）
```python
# agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

@dataclass
class AgentEvent:
    """Agent 统一事件模型。"""
    type: str   # "step" | "tool_result" | "done" | "max_steps" | "error"
    step: int
    data: dict[str, Any] = field(default_factory=dict)

class Agent(ABC):
    """Agent 抽象基类。"""
    @abstractmethod
    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        yield  # pragma: no cover
```

```python
# agents/agent_loop.py (修改部分)
from agent_framework.agents.base import Agent, AgentEvent

@dataclass
class LoopEvent(AgentEvent):
    """Agent Loop 每一步产生的事件。"""
    plan: PlanSnapshot | None = None

class AgentLoop(Agent):
    async def run(
        self,
        user_message: str,
        plan: list[PlanItem] | None = None,
        *,
        resume: bool = False,
    ) -> AsyncGenerator[LoopEvent, None]:
        # ... 现有实现不变 ...
```

### 类型标注更新（3 个文件各 1 处）
```python
# agents/sub_agent.py — 从
from agent_framework.agents.agent_loop import AgentLoop
# 改为
from agent_framework.agents.base import Agent
# 函数内 loop 变量类型标注：AgentLoop -> Agent (仅限类型标注，实际创建仍为 AgentLoop)
```

### PlanAndSolve 偏离检测规则检查
```python
# 规则检查（零额外成本）— 快速失败
def _rule_check_drift(self, result: str) -> bool | None:
    """返回 True=偏离, False=正常, None=需 LLM 评估。"""
    if not result or not result.strip():
        return True  # 空输出 = 偏离
    if "[子代理错误]" in result:
        return True  # 错误输出 = 偏离
    return None  # 规则无法判断，fallback 到 LLM
```

### ReflectionVerdict 容错解析
```python
import json

@dataclass
class ReflectionVerdict:
    """反省评估结论。"""
    satisfied: bool
    scores: dict[str, int]
    critique: str

    @classmethod
    def from_llm_response(cls, text: str) -> ReflectionVerdict:
        """从 LLM 响应解析 verdict，容错处理解析失败。"""
        # 尝试提取 JSON 块（LLM 可能在 JSON 前后加文字）
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return cls(
                    satisfied=bool(data.get("satisfied", False)),
                    scores=data.get("scores", {}),
                    critique=data.get("critique", ""),
                )
            except (json.JSONDecodeError, ValueError):
                pass
        # Fallback: 解析失败时默认不满意
        return cls(
            satisfied=False,
            scores={},
            critique=f"评估失败，原始输出：{text[:200]}",
        )
```

### 独立 LLM Completion 调用（Reflection 评估）
```python
async def _call_llm_for_evaluation(
    adapter: ILLMAdapter,
    model: str,
    prompt: str,
) -> str:
    """独立 LLM 调用，不走 AgentLoop 的 ReAct 循环。"""
    from agent_framework.llm.types import (
        CompletionConfig, CompletionResult,
        SystemMessage, UserMessage, TextBlock,
    )
    config = CompletionConfig(
        model=model,
        messages=[
            SystemMessage(content="你是一个输出质量评估专家。请严格按照 JSON 格式回复。"),
            UserMessage(content=[TextBlock(text=prompt)]),
        ],
        # 不传 tools，纯文本评估
    )
    result = await adapter.complete(config)
    # 提取文本
    for block in result.content:
        if isinstance(block, TextBlock):
            return block.text
    return ""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 单一 AgentLoop 做 ReAct | Agent ABC + 多种 Agent 类型 | Phase 6 | 架构扩展，不改现有行为 |
| 硬编码 AgentLoop 引用 | 面向 Agent 接口编程 | Phase 6 | runner/manager/sub_agent 面向抽象而非具体 |
| 无计划执行（纯 ReAct） | PlanAndSolve 先规划后执行 | Phase 6 | 复杂任务结构化执行 |
| 无自省能力 | Reflection 自评改进循环 | Phase 6 | 输出质量闭环提升 |

**Deprecated/outdated:**
- `agents/base.py` 空文件：从 scaffold 变为 Agent ABC + AgentEvent 的实现文件
- `agents/__init__.py` 空文件：从空变为导出 Agent、AgentEvent

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 协变返回类型允许 AgentLoop.run() 声明返回 LoopEvent 同时满足 Agent ABC 的 run() 签名 | Architecture Patterns | LOW — 已代码验证 |
| A2 | AgentLoop.run() 额外参数（plan, resume）不违反 ABC 契约 | Architecture Patterns | LOW — Python 运行时不检查，但类型检查器可能警告 |
| A3 | 截取最后 2000 字符足够作为步骤摘要（Claude's Discretion） | Common Pitfalls | MEDIUM — 如果单步输出超过 2000 字符会丢失信息 |
| A4 | LLM 评估偏离和三维度评估的 prompt 可以用简单模板实现 | Claude's Discretion | LOW — prompt 工程是迭代过程，初始版本可简单 |

## Open Questions

1. **PlanAndSolve 每步的 step 计数器如何全局管理？**
   - What we know: AgentEvent 需要 `step: int`，PlanAndSolve 内部有多步，每步又用 AgentLoop 执行多轮
   - What's unclear: `step` 是全局递增计数器（跨所有子步骤），还是每个 PlanAndSolve 步骤重置
   - Recommendation: 全局递增（每步执行或每个子 AgentLoop 事件都递增），便于消费者追踪总进度

2. **PlanAndSolve 执行步骤时是否转发子 AgentLoop 的事件？**
   - What we know: PlanAndSolve.run() 返回 AsyncGenerator[AgentEvent, None]
   - What's unclear: 步骤执行过程中 AgentLoop 产生的 LoopEvent 是否 yield 给调用者（作为 AgentEvent），还是只返回每步摘要
   - Recommendation: 转发子事件（LoopEvent 是 AgentEvent 子类），让消费者实时追踪进度

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | 运行时 | ✓ | 3.11.14 | — |
| pytest | 测试 | ✓ | 9.0.3 | — |
| httpx | LLM Adapter | ✓ | (已有) | — |
| pydantic | 类型定义 | ✓ | (已有) | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none — pytest 自动发现 tests/ 目录 |
| Quick run command | `cd framework && pytest tests/ -x -q` |
| Full suite command | `cd framework && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-01 | AgentEvent dataclass 字段和默认值 | unit | `pytest tests/test_agent_base.py -x` | Wave 0 |
| AGENT-02 | Agent ABC 不可实例化，子类必须实现 run() | unit | `pytest tests/test_agent_base.py -x` | Wave 0 |
| AGENT-03 | LoopEvent 继承 AgentEvent, AgentLoop 继承 Agent | unit | `pytest tests/test_agent_loop.py -x` | ✓ 现有 |
| AGENT-04 | 类型标注更新后 runner/manager/sub_agent 功能正常 | unit | `pytest tests/test_sub_agent.py tests/test_task_runner.py tests/test_teams_manager.py -x` | ✓ 现有 |
| AGENT-05 | 687 测试全部通过 | regression | `pytest tests/ -v` | ✓ 现有 |
| PLAN-01 | PlanAndSolveAgent 实例化和基本流程 | unit | `pytest tests/test_plan_and_solve.py -x` | Wave 0 |
| PLAN-02 | 计划生成调用 parse_plan_response | unit | `pytest tests/test_plan_and_solve.py::test_plan_generation -x` | Wave 0 |
| PLAN-03 | 每步独立 AgentLoop，步骤间无 context 累积 | unit | `pytest tests/test_plan_and_solve.py::test_step_isolation -x` | Wave 0 |
| PLAN-04 | 偏离检测 + replan 上限 2 次 | unit | `pytest tests/test_plan_and_solve.py::test_drift_detection -x` | Wave 0 |
| PLAN-05 | 空计划 fallback 到 ReAct | unit | `pytest tests/test_plan_and_solve.py::test_fallback -x` | Wave 0 |
| REFL-01 | ReflectionAgent 三阶段循环 | unit | `pytest tests/test_reflection.py -x` | Wave 0 |
| REFL-02 | ReflectionVerdict JSON 解析 + 容错 | unit | `pytest tests/test_reflection.py::test_verdict_parsing -x` | Wave 0 |
| REFL-03 | 改进轮次硬上限 2 次 | unit | `pytest tests/test_reflection.py::test_improvement_limit -x` | Wave 0 |
| REFL-04 | critique 注入下一轮用户消息 | unit | `pytest tests/test_reflection.py::test_critique_injection -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd framework && pytest tests/ -x -q`
- **Per wave merge:** `cd framework && pytest tests/ -v`
- **Phase gate:** Full suite green (687+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `framework/tests/test_agent_base.py` — covers AGENT-01, AGENT-02
- [ ] `framework/tests/test_plan_and_solve.py` — covers PLAN-01~05
- [ ] `framework/tests/test_reflection.py` — covers REFL-01~04
- [ ] MockAdapter 需要扩展：支持返回包含 `<plan>` 标签的响应（PlanAndSolve 测试用）

## Sources

### Primary (HIGH confidence)
- 代码库直接验证：AgentLoop.run() 返回 AsyncGenerator[LoopEvent, None] 已确认
- 代码库直接验证：LoopEvent dataclass 字段 `type, step, data, plan` 已确认
- 代码库直接验证：parse_plan_response() 解析逻辑 + 空计划处理已确认
- 代码库直接验证：PlanningState.check_drift() warn/abort 阈值逻辑已确认
- 代码库直接验证：create_filtered_router() 递归工具排除已确认
- 代码库直接验证：ABC 继承 + 协变返回类型在 Python 3.11.14 环境验证通过

### Secondary (MEDIUM confidence)
- CONTEXT.md 决策文档：13 个锁定决策 + 3 个 Claude's Discretion 区域
- ARCHITECTURE.md：AgentLoop 数据流、Tool Dispatch Pipeline、Sub-Agent Spawning Flow
- CONVENTIONS.md：dataclass 优先、AsyncGenerator 模式、不抛异常返回错误

### Tertiary (LOW confidence)
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 全部基于已验证的代码库内部组件
- Architecture: HIGH — ABC 继承 + 协变返回类型已代码验证，文件改动范围已锁定
- Pitfalls: HIGH — 基于 687 测试代码库的实际代码分析

**Research date:** 2026-05-29
**Valid until:** 2026-06-29（稳定，基于 Python 标准库和内部模块）
