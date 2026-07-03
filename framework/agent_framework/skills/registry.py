"""Skills 系统 — 多目录 Skill 注册表。"""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from xml.sax.saxutils import quoteattr

from agent_framework.config.loader import ConfigLoader
from agent_framework.skills.parser import (
    _parse_bool,
    _parse_list,
    _parse_paths,
    _parse_skill_document,
)
from agent_framework.skills.types import (
    SkillDocument,
    SkillLoadResult,
    SkillManifest,
    SkillSource,
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

    @classmethod
    def from_loader(cls, loader: ConfigLoader) -> SkillRegistry:
        """从 ConfigLoader.discover("skills") 路径创建注册表。

        discover() 返回 [global, project] 低到高优先级，
        反转后 [project, global] 传给 __init__ 的 first-found-wins 语义，
        使 project 级同名 skill 覆盖 global。
        """
        paths = loader.discover("skills")
        return cls(skills_dirs=list(reversed(paths)))

    def describe_available(self, names: list[str] | None = None) -> str:
        """L1: 轻量目录，注入 system prompt。自动检查更新。仅显示 active skills。

        names 给定时，只返回名单内的 active skill，并**按 names 列表顺序输出**(去重保序，
        保留 agent 配置里 skills 的声明顺序,LOW#6 review)。
        names=None 时返回全部并按名称排序（同原行为）。
        """
        self._maybe_refresh()
        active = {n: d for n, d in self._documents.items() if d.active}
        if names is not None:
            # M-1: 名单中不可用(未注册/inactive)的 skill 静默丢弃会让 agent 作者困惑,
            # 记 warning 暴露拼写错误 / skill 被 disable 等问题。
            missing = [n for n in names if n not in active]
            if missing:
                logger.warning("allowed_skills 中以下 skill 不可用/inactive,已忽略: %s", missing)
            ordered = list(dict.fromkeys(n for n in names if n in active))
        else:
            ordered = sorted(active)
        if not ordered:
            return "(没有可用的 skills)"
        lines = [f"- {name}: {active[name].manifest.description}" for name in ordered]
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

    def get_manifest(self, name: str) -> SkillManifest | None:
        """返回指定 skill 的 manifest，不存在返回 None。"""
        self._maybe_refresh()
        doc = self._documents.get(name)
        return doc.manifest if doc else None

    def is_trusted(self, name: str) -> bool:
        """判断 skill 是否可信。MCP 来源返回 False，其他来源返回 True。"""
        doc = self._documents.get(name)
        if doc is None:
            return False
        return doc.manifest.source != SkillSource.MCP

    def is_active(self, name: str) -> bool:
        """H-G7: 返回 skill 是否处于激活态。供 help 等外部模块查询，避免访问私有 _documents。"""
        doc = self._documents.get(name)
        return doc.active if doc is not None else False

    def activate_for_paths(self, file_paths: list[str]) -> list[str]:
        """检查文件路径，激活匹配的 inactive skills。

        遍历所有 inactive 的 skills，如果其 paths glob 模式
        匹配到任一 file_path，则激活该 skill。
        """
        activated: list[str] = []
        for name, doc in self._documents.items():
            if doc.active:
                continue
            paths = doc.manifest.paths
            if not paths:
                continue
            for pattern in paths:
                if any(self._glob_match(fp, pattern) for fp in file_paths):
                    self._documents[name] = SkillDocument(
                        manifest=doc.manifest, body=doc.body, active=True
                    )
                    activated.append(name)
                    break
        return activated

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
        root_resolved = root.resolve()
        for path in sorted(root.rglob("SKILL.md")):
            # G3: 剔除 symlink + 校验仍在 root 内，防路径遍历/递归炸弹
            if path.is_symlink():
                continue
            try:
                if not path.resolve().is_relative_to(root_resolved):
                    logger.warning("Skill 路径 %s 逃逸根目录，跳过", path)
                    continue
            except OSError:
                continue
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
            disable_model_invocation = _parse_bool(
                meta.get("disable-model-invocation"), default=False
            )
            context = meta.get("context")
            paths = _parse_paths(meta.get("paths"))

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
                source=SkillSource.USER,
                user_invocable=user_invocable,
                allowed_tools=allowed_tools,
                model=model,
                disable_model_invocation=disable_model_invocation,
                context=context,
                paths=paths,
            )
            # paths skills 默认 inactive
            active = not bool(paths)
            self._documents[name] = SkillDocument(
                manifest=manifest, body=body, active=active
            )

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
        ref_resolved = ref_dir.resolve()
        files: list[str] = []
        for f in ref_dir.rglob("*"):
            # G3: 剔除 symlink + 校验仍在 ref_dir 内，防路径遍历/递归炸弹
            if f.is_symlink() or not f.is_file():
                continue
            try:
                if not f.resolve().is_relative_to(ref_resolved):
                    continue
            except OSError:
                continue
            files.append(str(f.relative_to(ref_dir)))
        files.sort()
        return files[:10], len(files)

    @staticmethod
    def _glob_match(file_path: str, pattern: str) -> bool:
        """支持 ** 递归 glob 的路径匹配。

        PurePosixPath.match 要求 ** 至少匹配一层目录，
        但语义上 ** 应匹配零层或更多层，因此同时尝试两种情况。
        """
        p = PurePosixPath(file_path)
        if p.match(pattern):
            return True
        # ** 通常应匹配零层目录，尝试去掉 /** 的变体
        if "/**/" in pattern:
            # src/**/*.py → 同时尝试 src/*.py
            flat = pattern.replace("/**/", "/")
            if p.match(flat):
                return True
        if pattern.startswith("**/"):
            # **/foo.py → 同时尝试 foo.py
            flat = pattern[3:]
            if p.match(flat):
                return True
        return False
