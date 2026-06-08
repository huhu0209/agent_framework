"""Decomposer — LLM 驱动的任务分解：用户消息 → 子任务 DAG。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from agent_framework.llm.types import CompletionConfig, SystemMessage, TextBlock, UserMessage
from agent_framework.orchestrator.models import SubTask

if TYPE_CHECKING:
    from agent_framework.llm.base import ILLMAdapter
    from agent_framework.orchestrator.worker_registry import WorkerRegistry

_DECOMPOSE_SYSTEM_PROMPT = (
    "你是一个任务分解器。分析用户任务，将其分解为可由专业 Worker 执行的子任务。\n"
    "\n"
    "{worker_descriptions}\n"
    "\n"
    "规则：\n"
    "1. 每个子任务只分配给一个 Worker\n"
    "2. depends_on 填写前序子任务的 id（逗号分隔），无依赖留空\n"
    "3. prompt 要足够具体，让 Worker 知道该做什么\n"
    "4. 只输出 <decomposition> 标签，不要解释\n"
    "\n"
    "输出格式：\n"
    '<decomposition>\n'
    '<subtask id="1" worker="xxx" depends_on="">\n'
    "  具体指令\n"
    "</subtask>\n"
    "</decomposition>\n"
)

_MAX_PROMPT_LENGTH = 10_000


class Decomposer:
    """调用 LLM 将用户消息分解为 SubTask 列表（DAG）。"""

    _MAX_SUBTASKS = 20

    def __init__(self, adapter: ILLMAdapter, *, model: str) -> None:
        self._adapter = adapter
        self._model = model

    async def decompose(
        self, user_message: str, worker_registry: WorkerRegistry,
    ) -> list[SubTask]:
        """将用户消息分解为子任务列表。"""
        system_prompt = self._build_system_prompt(worker_registry)
        user_prompt = self._build_user_prompt(user_message)
        response = await self._call_llm(system_prompt, user_prompt)
        subtasks = self._parse_response(response)
        if subtasks is None:
            raise ValueError("Failed to parse decomposition from LLM response")
        self._validate(subtasks, worker_registry)
        return subtasks

    def _build_system_prompt(self, registry: WorkerRegistry) -> str:
        """构造发送给 LLM 的 system prompt。"""
        return _DECOMPOSE_SYSTEM_PROMPT.format(
            worker_descriptions=registry.describe_for_llm(),
        )

    def _build_user_prompt(self, user_message: str) -> str:
        """构造发送给 LLM 的 user prompt。"""
        return f"用户任务: {user_message}"

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM，返回文本响应。使用 SystemMessage + UserMessage 分离。"""
        config = CompletionConfig(
            model=self._model,
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=[TextBlock(text=user_prompt)]),
            ],
        )
        result = await self._adapter.complete(config)
        for block in result.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    def _parse_response(self, text: str) -> list[SubTask] | None:
        """从 LLM 响应中解析 <decomposition> XML 块。"""
        match = re.search(r"<decomposition>(.*?)</decomposition>", text, re.DOTALL)
        if not match:
            return None
        inner = match.group(1)
        subtask_pattern = re.compile(
            r'<subtask\s+id="([^"]+)"\s+worker="([^"]+)"\s+depends_on="([^"]*)">\s*(.*?)\s*</subtask>',
            re.DOTALL,
        )
        subtasks: list[SubTask] = []
        for m in subtask_pattern.finditer(inner):
            deps_str = m.group(3).strip()
            depends_on = (
                tuple(d.strip() for d in deps_str.split(",") if d.strip())
                if deps_str
                else ()
            )
            prompt_text = m.group(4).strip()
            if len(prompt_text) > _MAX_PROMPT_LENGTH:
                raise ValueError(
                    f"Subtask prompt too long: {len(prompt_text)} chars (max {_MAX_PROMPT_LENGTH})"
                )
            subtasks.append(SubTask(
                id=m.group(1),
                worker=m.group(2),
                prompt=prompt_text,
                depends_on=depends_on,
            ))
        if not subtasks:
            if "<subtask" in inner:
                raise ValueError(
                    "Failed to parse any subtask from <decomposition> block — likely malformed XML"
                )
            return None
        if len(subtasks) > self._MAX_SUBTASKS:
            raise ValueError(
                f"Too many subtasks: {len(subtasks)} (max {self._MAX_SUBTASKS})"
            )
        return subtasks

    def _validate(
        self, subtasks: list[SubTask], registry: WorkerRegistry,
    ) -> None:
        """验证子任务：worker 存在、依赖存在、无环。"""
        known_ids = {s.id for s in subtasks}
        id_to_task = {s.id: s for s in subtasks}
        for s in subtasks:
            try:
                registry.get(s.worker)
            except KeyError:
                raise ValueError(f"Worker not found: {s.worker}")
            for dep in s.depends_on:
                if dep not in known_ids:
                    raise ValueError(f"depends_on id '{dep}' not found in subtasks")

        # Cycle detection via iterative DFS
        visited: set[str] = set()
        in_stack: set[str] = set()

        for s in subtasks:
            if s.id in visited:
                continue
            stack: list[tuple[str, iter]] = [
                (s.id, iter(id_to_task[s.id].depends_on))
            ]
            in_stack.add(s.id)
            visited.add(s.id)

            while stack:
                node_id, deps_iter = stack[-1]
                try:
                    dep = next(deps_iter)
                    if dep in in_stack:
                        raise ValueError("Dependency cycle detected in subtasks")
                    if dep not in visited:
                        visited.add(dep)
                        in_stack.add(dep)
                        stack.append((dep, iter(id_to_task[dep].depends_on)))
                except StopIteration:
                    in_stack.discard(node_id)
                    stack.pop()
