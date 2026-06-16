"""MessageBus — JSONL 文件收件箱。"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path

from agent_framework.teams.types import TeamMessage

logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(self, team_dir: Path):
        self._dir = team_dir / "inbox"
        self._dir.mkdir(parents=True, exist_ok=True)

    def send(
        self, sender: str, to: str, content: str, *, msg_type: str = "message",
    ) -> TeamMessage:
        msg = TeamMessage(
            type=msg_type, from_=sender, to=to,
            content=content, timestamp=time.time(),
        )
        path = self._dir / f"{to}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps({
                "type": msg.type, "from_": msg.from_, "to": msg.to,
                "content": msg.content, "timestamp": msg.timestamp,
            }) + "\n")
        return msg

    def read_inbox(self, name: str) -> list[TeamMessage]:
        path = self._dir / f"{name}.jsonl"
        if not path.exists():
            return []
        raw = path.read_text()
        if not raw.strip():
            return []

        # 解析本次读到的消息 + 记录其原始行（用于精确清零）
        msgs: list[TeamMessage] = []
        read_lines: set[str] = set()
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                msgs.append(TeamMessage(**data))
                read_lines.add(stripped)
            except Exception:
                logger.debug("跳过无法解析的消息行: %s", stripped[:200])
                continue

        # H-G4: 精确清零——重读当前文件，只移除本次读到的消息行，
        # 保留 read 期间新追加的消息与不可解析行（不再清空整个文件）。
        current_raw = path.read_text()
        remaining = [
            line for line in current_raw.splitlines()
            if line.strip() and line.strip() not in read_lines
        ]
        output = ("\n".join(remaining) + "\n") if remaining else ""

        # 原子写回：write-to-temp + os.replace，防止崩溃时丢失
        fd, tmp_path = tempfile.mkstemp(
            dir=self._dir, suffix=".tmp", prefix=".inbox_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(output)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            logger.warning("原子清零收件箱失败: %s", path)

        return msgs

    def broadcast(self, sender: str, teammates: list[str], content: str) -> None:
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, msg_type="broadcast")
