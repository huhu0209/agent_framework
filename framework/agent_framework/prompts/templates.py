"""Prompt 模板 — 计划生成 + 偏离提醒。"""

PLAN_GENERATION_INSTRUCTION = """\
当收到复杂任务时，先制定执行计划。用以下格式输出：

<plan>
1. 第一步描述
2. 第二步描述
</plan>

每完成一步，调用 update_plan_status 工具更新状态。
简单任务不需要计划，直接执行即可。"""

DRIFT_WARN_PREFIX = "[偏离提醒]"

DRIFT_WARN_TEMPLATE = (
    DRIFT_WARN_PREFIX + " 你已经连续 {drift_count} 步没有推进计划中的任何项目。\n"
    "\n"
    "当前计划：\n"
    "{plan_text}\n"
    "\n"
    "请聚焦当前任务，或使用 update_plan_status 更新计划状态。"
)
