"""MessageBus — JSONL 文件收件箱。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from agent_framework.teams.types import TeamMessage


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
        raw = path.read_text().strip()
        path.write_text("")
        if not raw:
            return []
        msgs = []
        for line in raw.splitlines():
            try:
                data = json.loads(line)
                msgs.append(TeamMessage(**data))
            except Exception:
                continue
        return msgs

    def broadcast(self, sender: str, teammates: list[str], content: str) -> None:
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, msg_type="broadcast")
