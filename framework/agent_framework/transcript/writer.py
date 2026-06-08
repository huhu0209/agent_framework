"""JSONL 追加写入器。"""

import json
from dataclasses import asdict
from pathlib import Path

from agent_framework.transcript.types import TranscriptEvent


class TranscriptWriter:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def write(self, event: TranscriptEvent) -> None:
        data = asdict(event)
        data["type"] = event.type.value
        self._file.write(json.dumps(data, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
