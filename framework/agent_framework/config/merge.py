"""配置合并 — 类型感知的多层字典合并。"""

from __future__ import annotations

import copy


def merge_settings(*dicts: dict) -> dict:
    """合并多个配置字典，从低到高优先级。

    策略：
    - dict -> 递归浅合并（递归进入嵌套 dict，确保嵌套的 list[str] 也做并集）
    - list[str] -> 并集去重保序（低优先级在前）
    - 标量或其他类型不一致 -> 高优先级直接覆盖

    Args:
        *dicts: 配置字典，从低到高优先级。

    Returns:
        合并后的新字典（不修改输入）。
    """
    if not dicts:
        return {}

    result: dict = {}
    for d in dicts:
        for key, value in d.items():
            if key not in result:
                result[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = merge_settings(result[key], value)
            elif (
                isinstance(value, list)
                and isinstance(result[key], list)
                and all(isinstance(item, str) for item in result[key])
                and all(isinstance(item, str) for item in value)
            ):
                seen: set[str] = set()
                merged: list[str] = []
                for item in result[key] + value:
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[key] = merged
            else:
                result[key] = copy.deepcopy(value)
    return result
