"""Agent 事件流文本提取工具。"""

from __future__ import annotations


def extract_text_from_content(content: list, *, first_only: bool = False) -> str:
    """从 content blocks 提取 type=="text" 的文本。

    遍历 content，收集每个 dict 型 text block 的 text 字段：
    - first_only=True：返回首个匹配的 text（reflection 取首场景）。
    - first_only=False：拼接全部匹配 text（累加场景）。
    非 dict block、非 str text 安全跳过。
    """
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                if first_only:
                    return text
                texts.append(text)
    return "".join(texts)
