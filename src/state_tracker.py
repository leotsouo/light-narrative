"""人物與物品狀態追蹤（deterministic-first）。"""
from __future__ import annotations

import re

from src.narrative_patterns import (
    ACTIVE_SUBJECT_RE,
    DEAD_SUBJECT_RE,
    OBSERVER_DEATH_RE,
    PASSIVE_ACTIVE_RE,
    RESURRECT_SUBJECT_RE,
    filter_person_names,
    is_valid_holder_or_location,
    is_valid_person_name,
    is_valid_post_death_active_evidence,
    is_valid_source_evidence,
    split_sentences,
)
from src.schemas import CharacterState, Chunk, Event, ItemState, WorldRule


def derive_character_states(chunks: list[Chunk], character_names: list[str]) -> list[CharacterState]:
    """依明確句型追蹤角色狀態；觀察者不標記為死者。"""
    valid_names = set(filter_person_names(character_names))
    states: list[CharacterState] = []

    indexed: list[tuple[str, Chunk]] = []
    for chunk in chunks:
        for sent in split_sentences(chunk.text):
            indexed.append((sent, chunk))

    for idx, (sent, chunk) in enumerate(indexed):
        obs = OBSERVER_DEATH_RE.search(sent)
        if obs:
            antecedent = _resolve_antecedent(indexed, idx)
            if antecedent and antecedent in valid_names:
                ev = _find_death_evidence(indexed, idx, antecedent) or sent
                if is_valid_source_evidence(ev):
                    states.append(
                        CharacterState(
                            character=antecedent,
                            state="dead",
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=ev,
                        )
                    )
            continue

        for pattern in DEAD_SUBJECT_RE:
            for m in pattern.finditer(sent):
                name = m.group(1)
                if name not in valid_names:
                    continue
                if re.search(rf"在{name}", sent) and name.endswith(("山", "谷", "崖", "嶺", "河", "海")):
                    continue
                if not is_valid_source_evidence(sent):
                    continue
                states.append(
                    CharacterState(
                        character=name,
                        state="buried" if any(k in sent for k in ("安葬", "下葬", "埋葬")) else "dead",
                        chapter=chunk.chapter_title or None,
                        chunk_id=chunk.id,
                        evidence=sent,
                    )
                )

        rm = RESURRECT_SUBJECT_RE.search(sent)
        if rm:
            name = rm.group(1)
            if name in valid_names and is_valid_source_evidence(sent):
                states.append(
                    CharacterState(
                        character=name,
                        state="resurrected",
                        chapter=chunk.chapter_title or None,
                        chunk_id=chunk.id,
                        evidence=sent,
                    )
                )

        active_names: set[str] = set()
        for m in ACTIVE_SUBJECT_RE.finditer(sent):
            active_names.add(m.group(1))
        for m in PASSIVE_ACTIVE_RE.finditer(sent):
            active_names.add(m.group(1) or m.group(2))
        for name in active_names:
            if name not in valid_names:
                continue
            if any(p.search(sent) for p in DEAD_SUBJECT_RE):
                continue
            if OBSERVER_DEATH_RE.search(sent):
                continue
            if not is_valid_post_death_active_evidence(name, sent):
                continue
            states.append(
                CharacterState(
                    character=name,
                    state="active",
                    chapter=chunk.chapter_title or None,
                    chunk_id=chunk.id,
                    evidence=sent,
                )
            )

    return _dedupe_states(states)


def _resolve_antecedent(indexed: list[tuple[str, Chunk]], idx: int) -> str | None:
    for j in range(idx - 1, max(-1, idx - 6), -1):
        sent, _ = indexed[j]
        for pattern in DEAD_SUBJECT_RE:
            m = pattern.search(sent)
            if m:
                return m.group(1)
    return None


def _find_death_evidence(indexed: list[tuple[str, Chunk]], idx: int, name: str) -> str | None:
    for j in range(idx, max(-1, idx - 6), -1):
        sent, _ = indexed[j]
        if name in sent and any(k in sent for k in ("停止呼吸", "死亡", "身亡", "遇害")):
            return sent
    return None


def _resolve_item_holder(sent: str, item: str, prev_sents: list[str]) -> str | None:
    """解析「掛在自己腰間」「還在自己身上」等句的主語持有人。"""
    if "自己" not in sent and "自己" not in "".join(prev_sents[-1:]):
        return None
    if item not in sent and not any(item in p for p in prev_sents):
        return None
    blob = sent
    if "自己" not in blob:
        blob = (prev_sents[-1] if prev_sents else "") + sent
    if not re.search(rf"{re.escape(item)}[^。]{{0,25}}自己|自己[^。]{{0,25}}{re.escape(item)}", blob):
        if not re.search(rf"{re.escape(item)}.{{0,20}}(?:掛在|在)自己", sent):
            if not re.search(r"自己[^。]{0,20}(?:腰間|身上|外套|內袋)", sent):
                return None
    m_subj = re.match(r"^([\u4e00-\u9fff]{2,3})", sent.strip())
    if m_subj and is_valid_person_name(m_subj.group(1)) and m_subj.group(1) not in ("她", "他"):
        return m_subj.group(1)
    m_before = re.search(rf"([\u4e00-\u9fff]{{2,3}})[^。]{{0,40}}{re.escape(item)}", blob)
    if m_before and is_valid_person_name(m_before.group(1)) and m_before.group(1) not in ("她", "他"):
        return m_before.group(1)
    for prev in reversed(prev_sents):
        m_prev = re.match(r"^([\u4e00-\u9fff]{2,3})", prev.strip())
        if m_prev and is_valid_person_name(m_prev.group(1)) and m_prev.group(1) not in ("她", "他"):
            return m_prev.group(1)
    return None


def _dedupe_states(states: list[CharacterState]) -> list[CharacterState]:
    seen: set[tuple] = set()
    out: list[CharacterState] = []
    for s in states:
        key = (s.character, s.state, s.evidence)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def derive_item_states(
    chunks: list[Chunk], items: list[str], rules: list[WorldRule], events: list[Event]
) -> list[ItemState]:
    states: list[ItemState] = []
    item_set = {i for i in items if i and len(i) >= 2}

    for r in rules:
        if "唯一" in r.rule_text:
            for item in item_set:
                if item in r.rule_text:
                    states.append(
                        ItemState(
                            item=item,
                            property="unique",
                            chapter=r.chapter,
                            chunk_id=r.chunk_id,
                            evidence=r.evidence,
                        )
                    )

    for chunk in chunks:
        chunk_sents = split_sentences(chunk.text)
        for item in item_set:
            if item not in chunk.text:
                continue
            for si, sent in enumerate(chunk_sents):
                if item not in sent:
                    continue
                prev_sents = chunk_sents[max(0, si - 3) : si]
                # 持有人轉移
                m_give = re.search(
                    rf"([\u4e00-\u9fff]{{2,3}})把{re.escape(item)}(?:交給|交予|交還給|遞給)([\u4e00-\u9fff]{{2,3}})",
                    sent,
                )
                if m_give and is_valid_person_name(m_give.group(2)):
                    states.append(
                        ItemState(
                            item=item,
                            holder=m_give.group(2),
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=sent,
                        )
                    )
                holder = _resolve_item_holder(sent, item, prev_sents)
                if holder:
                    states.append(
                        ItemState(
                            item=item,
                            holder=holder,
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=sent,
                        )
                    )
                m_self = re.search(
                    rf"{re.escape(item)}.{{0,15}}(?:掛在|在)([\u4e00-\u9fff]{{2,3}})(?:腰間|身上|手中)",
                    sent,
                )
                if m_self and is_valid_person_name(m_self.group(1)) and m_self.group(1) != "自己":
                    states.append(
                        ItemState(
                            item=item,
                            holder=m_self.group(1),
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=sent,
                        )
                    )
                m_loc = re.search(
                    rf"{re.escape(item)}.{{0,20}}(?:在|於|出現在)([\u4e00-\u9fff]{{2,12}})",
                    sent,
                )
                if m_loc and is_valid_holder_or_location(m_loc.group(1)):
                    states.append(
                        ItemState(
                            item=item,
                            location=m_loc.group(1),
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=sent,
                        )
                    )
                if any(k in sent for k in ("拍賣會", "備用", "另一把", "第二把")) and item in sent:
                    states.append(
                        ItemState(
                            item=item,
                            property="possible_duplicate",
                            chapter=chunk.chapter_title or None,
                            chunk_id=chunk.id,
                            evidence=sent,
                        )
                    )

    for ev in events:
        if any(k in ev.evidence for k in ("備用", "另一把", "拍賣會")):
            for item in item_set:
                if item in ev.evidence or ("鑰匙" in item and "鑰匙" in ev.evidence):
                    states.append(
                        ItemState(
                            item=item,
                            property="possible_duplicate",
                            chapter=ev.chapter,
                            chunk_id=ev.chunk_id,
                            evidence=ev.evidence,
                        )
                    )

    return _dedupe_item_states(states)


def _dedupe_item_states(states: list[ItemState]) -> list[ItemState]:
    seen: set[tuple] = set()
    out: list[ItemState] = []
    for s in states:
        if s.holder and (not is_valid_holder_or_location(s.holder) or s.holder in ("自己", "她", "他")):
            continue
        if s.location and not is_valid_holder_or_location(s.location):
            continue
        key = (s.item, s.holder, s.location, s.property, s.evidence)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out
