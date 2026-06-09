"""角色資料合併與強化。"""
from __future__ import annotations

from src.schemas import Character


def merge_characters(characters: list[Character]) -> list[Character]:
    """依名稱合併特質、能力與狀態。"""
    by_name: dict[str, Character] = {}
    for c in characters:
        key = c.name.strip()
        if not key:
            continue
        if key not in by_name:
            by_name[key] = c.model_copy()
            continue
        existing = by_name[key]
        for t in c.traits:
            if t not in existing.traits:
                existing.traits.append(t)
        for a in c.abilities:
            if a not in existing.abilities:
                existing.abilities.append(a)
        existing.states.extend(c.states)
        if c.evidence and c.evidence not in (existing.evidence or ""):
            existing.evidence = (existing.evidence or "") + " | " + c.evidence
    return list(by_name.values())
