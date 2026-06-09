"""通用工具函式。"""
from __future__ import annotations

import json
import re
from typing import Any


def safe_json_loads(text: str) -> dict[str, Any] | list[Any] | None:
    """從 LLM 回應中擷取 JSON。"""
    text = text.strip()
    if not text:
        return None
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 找第一個 { ... }
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name.strip())


def unique_by_name(items: list, name_attr: str = "name") -> list:
    seen: set[str] = set()
    result = []
    for item in items:
        key = normalize_name(getattr(item, name_attr, ""))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def truncate(text: str, max_len: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def normalize_text(text: str) -> str:
    text = (text or "").strip()
    text = text.replace("。", "")
    text = text.replace("，", "")
    text = text.replace("：「", "")
    text = text.replace("」", "")
    return text
