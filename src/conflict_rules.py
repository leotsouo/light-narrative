"""規則式敘事衝突偵測（deterministic-first）。"""
from __future__ import annotations

import re
from collections import defaultdict

from src.narrative_patterns import (
    COMBAT_KEYWORDS,
    HIGH_ABILITY_KEYWORDS,
    LIMITATION_KEYWORDS,
    SETTING_EARLY_KEYWORDS,
    SETTING_REVERSAL_KEYWORDS,
    canonicalize_setting_entity,
    extract_setting_entity,
    extract_unique_item_from_rule,
    is_likely_world_rule,
    is_valid_post_death_active_evidence,
    is_valid_source_evidence,
    normalize_unique_item_name,
    split_sentences,
)
from src.schemas import CharacterState, ConflictReport, Event, ExtractionResult, WorldRule
from src.utils import normalize_text


def _make_conflict(
    project_id: str,
    conflict_type: str,
    severity: str,
    title: str,
    related: list[str],
    claim_a: str,
    claim_b: str,
    evidence_a: str,
    evidence_b: str,
    explanation: str,
    suggested_fix: str,
    chapters: list[str],
) -> ConflictReport | None:
    if not is_valid_source_evidence(evidence_a) or not is_valid_source_evidence(evidence_b):
        return None
    return ConflictReport(
        project_id=project_id,
        conflict_type=conflict_type,
        severity=severity,
        title=title,
        related_entities=related,
        claim_a=claim_a,
        claim_b=claim_b,
        evidence_a=evidence_a,
        evidence_b=evidence_b,
        explanation=explanation,
        suggested_fix=suggested_fix,
        chapters=[c for c in chapters if c],
    )


def canonical_conflict_key(c: ConflictReport) -> tuple:
    blob = normalize_text(c.title + c.claim_a + c.claim_b)
    if c.conflict_type == "world_rule_violation":
        if any(k in blob for k in ("復活", "亡者", "法術")):
            return ("world_rule_violation", "dead_cannot_resurrect")
        if any(k in blob for k in ("夜", "敲鐘", "黎明")):
            return ("world_rule_violation", "night_bell_rule")
    if c.conflict_type == "unique_item_conflict":
        item = c.related_entities[0] if c.related_entities else ""
        normalized = normalize_unique_item_name(item) or normalize_text(item)
        return ("unique_item_conflict", normalized)
    if c.conflict_type == "character_state_conflict":
        return ("character_state_conflict", tuple(sorted(c.related_entities)))
    if c.conflict_type == "world_setting_conflict":
        ent = c.related_entities[0] if c.related_entities else "setting"
        return ("world_setting_conflict", normalize_text(ent))
    if c.conflict_type == "character_consistency_drift":
        return ("character_consistency_drift", tuple(sorted(c.related_entities)))
    return (
        c.conflict_type,
        tuple(sorted(c.related_entities)),
        normalize_text(c.claim_a),
        normalize_text(c.claim_b),
    )


def _dedupe_merge(conflicts: list[ConflictReport]) -> list[ConflictReport]:
    merged: dict[tuple, ConflictReport] = {}
    for c in conflicts:
        key = canonical_conflict_key(c)
        if key not in merged:
            merged[key] = c
            continue
        existing = merged[key]
        if c.evidence_a and c.evidence_a not in existing.evidence_a:
            existing.evidence_a = (existing.evidence_a + "\n" + c.evidence_a).strip()
        if c.evidence_b and c.evidence_b not in existing.evidence_b:
            existing.evidence_b = (existing.evidence_b + "\n" + c.evidence_b).strip()
        for ch in c.chapters:
            if ch not in existing.chapters:
                existing.chapters.append(ch)
    return list(merged.values())


def rule1_dead_then_active(character_states: list[CharacterState], project_id: str) -> list[ConflictReport]:
    conflicts: list[ConflictReport] = []
    by_char: dict[str, list[CharacterState]] = defaultdict(list)
    for s in character_states:
        if "相關描述" in s.evidence:
            continue
        by_char[s.character].append(s)

    for char, states in by_char.items():
        dead_states = [s for s in states if s.state in ("dead", "buried")]
        active_states = [
            s
            for s in states
            if s.state == "active" and is_valid_post_death_active_evidence(char, s.evidence)
        ]
        if not dead_states or not active_states:
            continue
        dead = dead_states[0]
        active = active_states[0]
        c = _make_conflict(
            project_id=project_id,
            conflict_type="character_state_conflict",
            severity="high",
            title=f"角色「{char}」死亡/安葬後仍活動",
            related=[char],
            claim_a=f"{char} 在文本中被明確描述為死亡或安葬",
            claim_b=f"{char} 之後仍出現說話、行動或參與事件",
            evidence_a=dead.evidence,
            evidence_b=active.evidence,
            explanation="同一角色在死亡或安葬後仍出現活動描述，可能造成時間線或設定矛盾。",
            suggested_fix="若為伏筆/復活，請補充明確機制；否則調整事件先後或刪改其中一段描述。",
            chapters=[dead.chapter or "", active.chapter or ""],
        )
        if c:
            conflicts.append(c)
    return conflicts


def _resurrection_rules(rules: list[WorldRule]) -> list[WorldRule]:
    return [
        r
        for r in rules
        if any(k in r.rule_text for k in ("亡者不能", "不能被任何法術復活", "不得復活", "無法復活"))
    ]


def _resurrection_events(events: list[Event]) -> list[Event]:
    out: list[Event] = []
    for ev in events:
        blob = f"{ev.action} {ev.evidence}"
        if any(k in blob for k in ("復活", "從火焰中走出", "走出火焰", "被鐘復活")):
            if is_valid_source_evidence(ev.evidence):
                out.append(ev)
    return out


def rule2_dead_cannot_resurrect(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:
    r_rules = _resurrection_rules(rules)
    r_events = _resurrection_events(events)
    if not r_rules or not r_events:
        return []
    best_rule = max(r_rules, key=lambda r: len(r.evidence))
    best_event = r_events[0]
    subject = best_event.subject or "角色"
    c = _make_conflict(
        project_id=project_id,
        conflict_type="world_rule_violation",
        severity="high",
        title="復活違反「亡者不能復活」世界規則",
        related=[subject, "亡者"],
        claim_a="文本設定亡者不能被復活（或同等禁忌）。",
        claim_b="後文事件描述角色復活、重返或從死亡狀態出現。",
        evidence_a=best_rule.evidence,
        evidence_b=best_event.evidence,
        explanation="世界觀規則禁止亡者復活，但事件呈現復活或重返的結果。",
        suggested_fix="若要允許復活，需補充例外條件/代價/機制；否則改寫事件結果。",
        chapters=[best_rule.chapter or "", best_event.chapter or ""],
    )
    return [c] if c else []


def rule3_unique_item(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:
    conflicts: list[ConflictReport] = []
    seen_items: set[str] = set()
    for r in rules:
        if "唯一" not in r.rule_text:
            continue
        item = extract_unique_item_from_rule(r.rule_text)
        if not item:
            continue
        norm_item = normalize_unique_item_name(item)
        if not norm_item or norm_item in seen_items:
            continue
        dup_events = [
            ev
            for ev in events
            if is_valid_source_evidence(ev.evidence)
            and any(k in ev.evidence for k in ("備用", "另一把", "第二把", "又有一把", "拍賣會"))
            and (norm_item in ev.evidence or (norm_item.endswith("鑰匙") and "鑰匙" in ev.evidence))
        ]
        if not dup_events:
            continue
        seen_items.add(norm_item)
        ev = dup_events[0]
        c = _make_conflict(
            project_id=project_id,
            conflict_type="unique_item_conflict",
            severity="high",
            title=f"唯一物品「{norm_item}」出現矛盾",
            related=[norm_item],
            claim_a=f"文本宣稱「{norm_item}」具有唯一性（或唯一功能）。",
            claim_b="後文出現備用、另一把或同功能替代品。",
            evidence_a=r.evidence,
            evidence_b=ev.evidence,
            explanation="先宣稱物品唯一，後續卻出現備用品或同功能替代品，可能造成設定矛盾。",
            suggested_fix="若確有多把，請改寫「唯一」的範圍或補上來源差異；否則移除備用描述。",
            chapters=[r.chapter or "", ev.chapter or ""],
        )
        if c:
            conflicts.append(c)
    return conflicts


def rule4_item_location_holder(item_states, project_id: str) -> list[ConflictReport]:
    conflicts: list[ConflictReport] = []
    by_item: dict[str, list] = defaultdict(list)
    for s in item_states:
        by_item[s.item].append(s)

    invalid_holders = {"自己", "她", "他"}

    for item, states in by_item.items():
        holders = [s for s in states if s.holder and s.holder not in invalid_holders]
        unique_holders = {h.holder for h in holders}
        if len(unique_holders) <= 1:
            continue
        a, b = holders[0], holders[-1]
        if a.holder == b.holder:
            continue
        c = _make_conflict(
            project_id=project_id,
            conflict_type="item_location_conflict",
            severity="medium",
            title=f"物品「{item}」持有人不一致",
            related=[item],
            claim_a=f"段落 A 記錄持有人為「{a.holder}」。",
            claim_b=f"段落 B 記錄持有人為「{b.holder}」。",
            evidence_a=a.evidence,
            evidence_b=b.evidence,
            explanation="同一物品在不同段落出現不同持有人，若無交接描寫可能造成矛盾。",
            suggested_fix="補上物品交接/遺失/拾獲的描寫，或統一持有人設定。",
            chapters=[a.chapter or "", b.chapter or ""],
        )
        if c:
            conflicts.append(c)
    return conflicts


def _night_bell_rules(rules: list[WorldRule]) -> list[WorldRule]:
    return [
        r
        for r in rules
        if "夜" in r.rule_text and any(k in r.rule_text for k in ("敲鐘", "敲響", "鐘", "黎明"))
    ]


def _night_bell_events(events: list[Event]) -> list[Event]:
    out: list[Event] = []
    for ev in events:
        if not is_valid_source_evidence(ev.evidence):
            continue
        if is_likely_world_rule(ev.evidence):
            continue
        time_blob = f"{ev.time or ''} {ev.evidence}"
        if any(t in time_blob for t in ("夜半", "夜晚", "夜間")) and any(
            k in ev.evidence for k in ("敲鐘", "敲響", "拉下", "響起")
        ):
            out.append(ev)
    return out


def rule5_night_bell(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:
    bell_rules = _night_bell_rules(rules)
    bell_events = _night_bell_events(events)
    if not bell_rules or not bell_events:
        return []
    best_rule = max(bell_rules, key=lambda r: len(r.evidence))
    best_event = bell_events[0]
    related = list({best_event.subject, "敲鐘", "夜晚"} - {None})
    c = _make_conflict(
        project_id=project_id,
        conflict_type="world_rule_violation",
        severity="high",
        title="夜晚敲鐘規則被違反",
        related=[x for x in related if x],
        claim_a="文本設定夜晚敲鐘會帶來負面後果，或僅限特定時段敲鐘。",
        claim_b="後文出現夜間敲鐘的實際行動。",
        evidence_a=best_rule.evidence,
        evidence_b=best_event.evidence,
        explanation="世界觀規則限制夜晚敲鐘，但事件描述在夜間執行敲鐘。",
        suggested_fix="若要敲鐘，需補上例外/代價/防護；或將事件時間改為允許的時段。",
        chapters=[best_rule.chapter or "", best_event.chapter or ""],
    )
    return [c] if c else []


def _collect_profile_sentences(extraction: ExtractionResult) -> list[tuple[str | None, str, str | None]]:
    """(subject_hint, sentence, chapter) 供角色限制/能力比對。"""
    rows: list[tuple[str | None, str, str | None]] = []
    for c in extraction.characters:
        for trait in c.traits:
            rows.append((c.name, trait, None))
        if c.evidence:
            for sent in split_sentences(c.evidence):
                rows.append((c.name, sent, None))
    for ev in extraction.events:
        if ev.evidence and is_valid_source_evidence(ev.evidence):
            rows.append((ev.subject, ev.evidence, ev.chapter))
    for r in extraction.world_rules:
        if r.evidence and is_valid_source_evidence(r.evidence):
            rows.append((None, r.evidence, r.chapter))
    return rows


def _infer_character_from_sentence(sent: str, names: list[str]) -> str | None:
    for name in names:
        if name in sent:
            return name
    m = re.match(r"^([\u4e00-\u9fff]{2,3})", sent.strip())
    if m and m.group(1) in names:
        return m.group(1)
    m2 = re.match(r"^(她|他)", sent.strip())
    if m2:
        return None
    return None


def _limitation_contradicts_behavior(lim_sent: str, act_sent: str) -> bool:
    lim = lim_sent
    act = act_sent
    combat_lim = any(k in lim for k in ("不擅", "不會", "無法", "不能", "膽小", "畏縮", "容易退縮"))
    combat_act = any(k in act for k in COMBAT_KEYWORDS + ("擊敗", "熟練", "制服", "無畏", "衝鋒"))
    if combat_lim and combat_act:
        return True
    fear_lim = any(k in lim for k in ("害怕", "不敢"))
    fear_act = any(k in act for k in ("毫不畏懼", "無畏", "獨自走進", "走進"))
    if fear_lim and fear_act:
        return True
    if any(k in lim for k in LIMITATION_KEYWORDS) and any(k in act for k in HIGH_ABILITY_KEYWORDS):
        return True
    return False


def rule6_character_drift(extraction: ExtractionResult, project_id: str) -> list[ConflictReport]:
    conflicts: list[ConflictReport] = []
    names = [c.name for c in extraction.characters]
    if not names:
        return []

    limitation_by_char: dict[str, str] = {}
    combat_by_char: dict[str, str] = {}

    for c in extraction.characters:
        for trait in c.traits:
            if any(k in trait for k in LIMITATION_KEYWORDS):
                limitation_by_char.setdefault(c.name, trait)

    rows = _collect_profile_sentences(extraction)
    last_named: str | None = None
    for subj_hint, sent, _chapter in rows:
        name = subj_hint or _infer_character_from_sentence(sent, names)
        if name:
            last_named = name
        if any(k in sent for k in LIMITATION_KEYWORDS):
            who = name or last_named
            if who and who in names:
                limitation_by_char.setdefault(who, sent)
        if any(k in sent for k in HIGH_ABILITY_KEYWORDS):
            who = name
            if not who and sent.strip().startswith(("她", "他")) and last_named:
                who = last_named
            if not who:
                who = _infer_character_from_sentence(sent, names)
            if who and who in names:
                lim = limitation_by_char.get(who)
                if lim and _limitation_contradicts_behavior(lim, sent):
                    combat_by_char.setdefault(who, sent)

    for name, lim_ev in limitation_by_char.items():
        combat_ev = combat_by_char.get(name)
        if not combat_ev:
            continue
        c = _make_conflict(
            project_id=project_id,
            conflict_type="character_consistency_drift",
            severity="medium",
            title=f"角色「{name}」能力或性格表現出現漂移",
            related=[name],
            claim_a="前文設定角色有某種限制、弱點或不擅長事項。",
            claim_b="後文角色表現出與該限制不一致的能力或行為。",
            evidence_a=lim_ev,
            evidence_b=combat_ev,
            explanation="這可能是角色成長、伏筆或設定矛盾，需要作者確認並補充鋪陳。",
            suggested_fix="若是角色成長，請補上訓練、心理轉折或能力覺醒；若不是，請調整後文行為強度。",
            chapters=[],
        )
        if c:
            conflicts.append(c)
    return conflicts


def rule7_world_setting(rules: list[WorldRule], project_id: str) -> list[ConflictReport]:
    conflicts: list[ConflictReport] = []
    by_entity: dict[str, list[WorldRule]] = defaultdict(list)
    raw_entities: list[str] = []
    for r in rules:
        ent = extract_setting_entity(r.rule_text) or r.subject
        if ent and len(ent) >= 2:
            raw_entities.append(ent)
            by_entity[ent].append(r)

    all_entities = list({canonicalize_setting_entity(e, raw_entities) for e in raw_entities})
    all_entities = [e for e in all_entities if e and len(e) >= 2]

    merged: dict[str, list[WorldRule]] = defaultdict(list)
    for ent, group in by_entity.items():
        canon = canonicalize_setting_entity(ent, all_entities)
        if not canon or len(canon) <= 1:
            continue
        merged[canon].extend(group)

    for ent, group in merged.items():
        early: WorldRule | None = None
        late: WorldRule | None = None
        for r in group:
            if any(k in r.rule_text for k in SETTING_EARLY_KEYWORDS):
                early = early or r
            if any(k in r.rule_text for k in SETTING_REVERSAL_KEYWORDS):
                late = late or r
        if early and late and early.evidence != late.evidence:
            c = _make_conflict(
                project_id=project_id,
                conflict_type="world_setting_conflict",
                severity="medium",
                title=f"「{ent}」相關世界設定出現重大反轉",
                related=[ent],
                claim_a="前文建立的核心設定或位置/功能描述。",
                claim_b="後文揭示設定被推翻、移動或替換。",
                evidence_a=early.evidence,
                evidence_b=late.evidence,
                explanation="這可能是劇情反轉，不一定是錯誤，但屬於重大設定變更，需要作者補充伏筆或解釋。",
                suggested_fix="在反轉前加入暗示，或在反轉當下補充可信的因果與資訊來源。",
                chapters=[early.chapter or "", late.chapter or ""],
            )
            if c:
                conflicts.append(c)
    return conflicts


def detect_all_conflicts(extraction: ExtractionResult) -> list[ConflictReport]:
    project_id = ""
    if extraction.world_rules:
        project_id = extraction.world_rules[0].project_id
    elif extraction.events:
        project_id = extraction.events[0].project_id

    conflicts: list[ConflictReport] = []
    conflicts.extend(rule1_dead_then_active(extraction.character_states, project_id))
    conflicts.extend(rule2_dead_cannot_resurrect(extraction.world_rules, extraction.events, project_id))
    conflicts.extend(rule3_unique_item(extraction.world_rules, extraction.events, project_id))
    conflicts.extend(rule4_item_location_holder(extraction.item_states, project_id))
    conflicts.extend(rule5_night_bell(extraction.world_rules, extraction.events, project_id))
    conflicts.extend(rule6_character_drift(extraction, project_id))
    conflicts.extend(rule7_world_setting(extraction.world_rules, project_id))

    conflicts = _dedupe_merge([c for c in conflicts if c is not None])

    severity_order = {"high": 0, "medium": 1, "low": 2}
    conflicts.sort(key=lambda c: severity_order.get(c.severity, 9))
    return conflicts
