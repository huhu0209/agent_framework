"""记忆搜索共用工具。"""

from __future__ import annotations

import re

# 按 ## 标题切块（保留分隔行）
_BLOCK_SPLIT_RE = re.compile(r"(?=^## )", flags=re.MULTILINE)


def search_blocks(content: str, query: str) -> list[str]:
    """按 ## 标题切块，返回含 query（子串、大小写不敏感）的块（已 strip）。

    供 episodic 关键词搜索复用（search.py 的 handle_memory_search 与
    store.py 的 _search_episodic）。top_k 截断由调用方负责。
    """
    query_lower = query.lower()
    return [
        block.strip()
        for block in _BLOCK_SPLIT_RE.split(content)
        if block.strip() and query_lower in block.lower()
    ]
