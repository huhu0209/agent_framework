"""WorkerRegistry — 管理 WorkerSpec 的注册、查询与 LLM 描述生成。"""

from __future__ import annotations

import re

from agent_framework.orchestrator.models import WorkerSpec


class WorkerRegistry:
    _VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')

    def __init__(self) -> None:
        self._workers: dict[str, WorkerSpec] = {}

    def register(self, spec: WorkerSpec) -> None:
        if not spec.name or not spec.name.strip():
            raise ValueError("Worker name cannot be empty")
        if not self._VALID_NAME_PATTERN.match(spec.name):
            raise ValueError(f"Invalid worker name: {spec.name!r}")
        if spec.name in self._workers:
            raise ValueError(f"Worker already registered: {spec.name}")
        self._workers[spec.name] = spec

    def get(self, name: str) -> WorkerSpec:
        if name not in self._workers:
            raise KeyError(f"Worker not found: {name}")
        return self._workers[name]

    def has_workers(self) -> bool:
        return len(self._workers) > 0

    def describe_for_llm(self) -> str:
        """生成 Worker 列表的 LLM 可读描述。"""
        if not self._workers:
            return "可用 Worker 列表：无"
        lines = ["可用 Worker 列表："]
        for spec in self._workers.values():
            lines.append(f"- {spec.name}: {spec.description}")
        return "\n".join(lines)
