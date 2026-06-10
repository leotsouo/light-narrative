"""實體抽取：角色、地點、物品、世界規則。"""
from __future__ import annotations

import re

from src.llm_client import BaseLLMProvider
from src.narrative_patterns import (
    ACTIVE_SUBJECT_RE,
    DEAD_SUBJECT_RE,
    LIMITATION_KEYWORDS,
    extract_object_names_from_text,
    filter_person_names,
    is_likely_world_rule,
    is_valid_person_name,
    split_sentences,
)
from src.schemas import Character, Chunk, ExtractionResult, Location, StoryObject, WorldRule
from src.utils import safe_json_loads, unique_by_name

ENTITY_SYSTEM = """你是敘事分析助手，只抽取文本中明確出現的資訊，不創作情節。
以 JSON 回覆，格式：
{
  "characters": [{"name": "", "traits": [], "abilities": [], "evidence": ""}],
  "locations": [{"name": "", "description": "", "evidence": ""}],
  "objects": [{"name": "", "location": null, "owner": null, "evidence": ""}],
  "world_rules": [{"rule_text": "", "evidence": ""}]
}
只輸出 JSON。"""


def _extract_names_from_text(text: str) -> list[str]:
    names: set[str] = set()
    for sent in split_sentences(text):
        s = sent.strip()
        for pattern in DEAD_SUBJECT_RE:
            for m in pattern.finditer(s):
                if is_valid_person_name(m.group(1)):
                    names.add(m.group(1))
        m_active = ACTIVE_SUBJECT_RE.match(s)
        if m_active and is_valid_person_name(m_active.group(1)):
            names.add(m_active.group(1))
        for m in re.finditer(r"([\u4e00-\u9fff]{2,4})(?:說道|問道|笑道|喊道)", s):
            if is_valid_person_name(m.group(1)):
                names.add(m.group(1))
        m_start = re.match(r"^([\u4e00-\u9fff]{2})(?=[，,、\s]|[^一-龥]|$)", s)
        if m_start and is_valid_person_name(m_start.group(1)):
            names.add(m_start.group(1))
        if any(k in s for k in LIMITATION_KEYWORDS):
            m_lim = re.match(r"^([\u4e00-\u9fff]{2})", s)
            if m_lim and is_valid_person_name(m_lim.group(1)):
                names.add(m_lim.group(1))
    return filter_person_names(list(names))


def _extract_traits_for_character(text: str, name: str) -> list[str]:
    traits: list[str] = []
    for sent in split_sentences(text):
        if name not in sent:
            continue
        if any(k in sent for k in LIMITATION_KEYWORDS):
            traits.append(sent.strip())
    return traits


def extract_entities_heuristic(chunk: Chunk) -> ExtractionResult:
    text = chunk.text
    project_id = chunk.project_id

    name_list = _extract_names_from_text(text)
    characters = [
        Character(
            project_id=project_id,
            name=n,
            traits=_extract_traits_for_character(text, n),
            source_chunk_id=chunk.id,
            evidence=text[:120],
        )
        for n in name_list
    ]

    loc_hits = set(re.findall(r"在([\u4e00-\u9fff]{2,8})(?:裡|中|內|上|外)", text))
    locations = [
        Location(
            project_id=project_id,
            name=n,
            source_chunk_id=chunk.id,
            evidence=text[:120],
        )
        for n in loc_hits
        if len(n) >= 2
    ]

    obj_names = extract_object_names_from_text(text)
    objects = [
        StoryObject(
            project_id=project_id,
            name=n,
            source_chunk_id=chunk.id,
            evidence=text[:120],
        )
        for n in obj_names
    ]

    rules: list[WorldRule] = []
    for sent in split_sentences(text):
        if not is_likely_world_rule(sent):
            continue
        rule_text = sent.strip()
        subject = None
        condition = None
        constraint = None
        if "亡者" in rule_text or "復活" in rule_text:
            subject = "亡者"
            constraint = "復活"
        if "夜" in rule_text:
            condition = "夜晚"
        if "敲鐘" in rule_text or "鐘" in rule_text:
            subject = subject or "鐘"
            constraint = constraint or "敲鐘"
        rules.append(
            WorldRule(
                project_id=project_id,
                rule_text=rule_text,
                subject=subject,
                constraint=constraint,
                condition=condition,
                exception=None,
                chapter=chunk.chapter_title or None,
                chunk_id=chunk.id,
                evidence=rule_text,
            )
        )

    return ExtractionResult(
        characters=characters,
        locations=locations,
        objects=objects,
        world_rules=rules,
    )


def extract_entities_llm(chunk: Chunk, llm: BaseLLMProvider) -> ExtractionResult:
    prompt = f"標題：{chunk.chapter_title}\n\n文本：\n{chunk.text[:3000]}"
    raw = llm.complete(prompt, system=ENTITY_SYSTEM)
    data = safe_json_loads(raw)
    if not isinstance(data, dict):
        return extract_entities_heuristic(chunk)

    project_id = chunk.project_id
    characters = [
        Character(
            project_id=project_id,
            name=item.get("name", ""),
            traits=item.get("traits", []),
            abilities=item.get("abilities", []),
            source_chunk_id=chunk.id,
            evidence=item.get("evidence", ""),
        )
        for item in data.get("characters", [])
        if is_valid_person_name(item.get("name", ""))
    ]
    locations = [
        Location(
            project_id=project_id,
            name=item.get("name", ""),
            description=item.get("description", ""),
            source_chunk_id=chunk.id,
            evidence=item.get("evidence", ""),
        )
        for item in data.get("locations", [])
        if item.get("name")
    ]
    objects = [
        StoryObject(
            project_id=project_id,
            name=item.get("name", ""),
            location=item.get("location"),
            owner=item.get("owner"),
            source_chunk_id=chunk.id,
            evidence=item.get("evidence", ""),
        )
        for item in data.get("objects", [])
        if item.get("name")
    ]
    rules = [
        WorldRule(
            project_id=project_id,
            rule_text=item.get("rule_text", item.get("rule", "")),
            subject=item.get("subject"),
            constraint=item.get("constraint"),
            condition=item.get("condition"),
            exception=item.get("exception"),
            chapter=chunk.chapter_title or None,
            chunk_id=chunk.id,
            evidence=item.get("evidence", ""),
        )
        for item in data.get("world_rules", [])
        if item.get("rule_text") or item.get("rule")
    ]
    return ExtractionResult(
        characters=characters,
        locations=locations,
        objects=objects,
        world_rules=rules,
    )


def merge_extractions(parts: list[ExtractionResult]) -> ExtractionResult:
    chars: list[Character] = []
    locs: list[Location] = []
    objs: list[StoryObject] = []
    rules: list[WorldRule] = []
    events = []
    char_states = []
    item_states = []
    for p in parts:
        chars.extend(p.characters)
        locs.extend(p.locations)
        objs.extend(p.objects)
        rules.extend(p.world_rules)
        events.extend(p.events)
        char_states.extend(p.character_states)
        item_states.extend(p.item_states)
    return ExtractionResult(
        characters=unique_by_name(chars),
        locations=unique_by_name(locs),
        objects=unique_by_name(objs),
        world_rules=rules,
        events=events,
        character_states=char_states,
        item_states=item_states,
    )
