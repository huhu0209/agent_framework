"""Skills 系统 — 多目录 Skill 注册表。"""

from __future__ import annotations

import logging
from pathlib import Path
from xml.sax.saxutils import quoteattr

from agent_framework.skills.manifest import (
    SkillDocument,
    SkillLoadResult,
    SkillManifest,
    _parse_bool,
    _parse_list,
    _parse_skill_document,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """多目录 Skill 注册表，按优先级扫描。

    同名 skill 保留先扫描到的（personal > project）。
    通过 mtime 检查实现自动发现。
    """

    def __init__(self, skills_dirs: list[Path]) -> None:
        self._dirs = skills_dirs
        self._documents: dict[str, SkillDocument] = {}
        self._dir_mtimes: dict[Path, float] = {}
        self._full_refresh()

    def describe_available(self) -> str:
        """L1: 轻量目录，注入 system prompt。自动检查更新。"""
        self._maybe_refresh()
        if not self._documents:
            return "(没有可用的 skills)"
        lines = []
        for name in sorted(self._documents):
            doc = self._documents[name]
            lines.append(f"- {name}: {doc.manifest.description}")
        return "\n".join(lines)

    def load_full_text(self, name: str) -> SkillLoadResult:
        """L2: 完整 skill 正文 + references 索引。自动检查更新。"""
        self._maybe_refresh()
        doc = self._documents.get(name)
        if doc is None:
            known = ", ".join(sorted(self._documents)) or "(无)"
            return SkillLoadResult(
                content=f"未知 skill '{name}'。可用 skills: {known}",
                is_error=True,
            )
        return SkillLoadResult(content=self._format_skill_body(doc))

    def get_names(self) -> list[str]:
        """返回所有已注册 skill 名称。"""
        return sorted(self._documents.keys())

    def refresh(self) -> None:
        """强制全量重新扫描。"""
        self._full_refresh()

    # ---- 内部方法 ----

    def _maybe_refresh(self) -> None:
        needs_refresh = False
        for d in self._dirs:
            if not d.exists():
                continue
            try:
                current_mtime = d.stat().st_mtime
            except OSError:
                continue
            if self._dir_mtimes.get(d, 0) < current_mtime:
                needs_refresh = True
                break
        if needs_refresh:
            self._full_refresh()

    def _full_refresh(self) -> None:
        self._documents = {}
        self._dir_mtimes = {}
        for d in self._dirs:
            try:
                if d.exists():
                    self._scan_dir(d)
                    self._dir_mtimes[d] = d.stat().st_mtime
            except OSError:
                logger.warning("无法访问 skill 目录 %s，跳过", d)

    def _scan_dir(self, root: Path) -> None:
        if not root.exists():
            return
        for path in sorted(root.rglob("SKILL.md")):
            try:
                raw = path.read_text(encoding="utf-8")
            except Exception:
                logger.warning("无法读取 %s，跳过", path)
                continue

            meta, body = _parse_skill_document(raw)

            name = meta.get("name") or path.parent.name
            description = meta.get("description", "No description")
            user_invocable = _parse_bool(meta.get("user-invocable"), default=True)
            allowed_tools = _parse_list(meta.get("allowed-tools"))
            model = meta.get("model")

            if "name" not in meta:
                logger.warning(
                    "SKILL.md at %s 缺 name 字段，使用目录名 '%s'", path, name
                )
            if "description" not in meta:
                logger.warning(
                    "Skill '%s' 缺 description 字段，LLM 不会主动触发", name
                )

            if name in self._documents:
                continue

            manifest = SkillManifest(
                name=name,
                description=description,
                path=path.parent,
                user_invocable=user_invocable,
                allowed_tools=allowed_tools,
                model=model,
            )
            self._documents[name] = SkillDocument(manifest=manifest, body=body)

    def _format_skill_body(self, doc: SkillDocument) -> str:
        parts = [
            f"<skill name={quoteattr(doc.manifest.name)}>",
            f"描述：{doc.manifest.description}",
            doc.body,
            "</skill>",
        ]
        refs, total = self._list_references(doc.manifest.path)
        if refs:
            parts.append("\n此 skill 包含以下参考文档，可用 read_file 按需加载：")
            for rel_path in refs:
                parts.append(f"- references/{rel_path}")
            remaining = total - len(refs)
            if remaining > 0:
                parts.append(f"- ... 还有 {remaining} 个文件未显示")
        return "\n".join(parts)

    def _list_references(self, skill_dir: Path) -> tuple[list[str], int]:
        """返回 (文件列表最多10个, 总数)。"""
        ref_dir = skill_dir / "references"
        if not ref_dir.is_dir():
            return [], 0
        files = sorted(
            str(f.relative_to(ref_dir))
            for f in ref_dir.rglob("*")
            if f.is_file()
        )
        return files[:10], len(files)
