"""WorkerRegistry — 管理 WorkerSpec 的注册、查询与 LLM 描述生成。"""

from __future__ import annotations

from agent_framework.orchestrator.models import WorkerSpec


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, WorkerSpec] = {}

    def register(self, spec: WorkerSpec) -> None:
        self._workers[spec.name] = spec

    def get(self, name: str) -> WorkerSpec:
        if name not in self._workers:
            raise KeyError(f"Worker not found: {name}")
        return self._workers[name]

    def has_workers(self) -> bool:
        return len(self._workers) > 0

    def describe_for_llm(self) -> str:
        if not self._workers:
            return "无可用 Worker"
        lines = ["可用 Worker 列表："]
        for spec in self._workers.values():
            lines.append(f"- {spec.name}: {spec.description}")
        return "\n".join(lines)
