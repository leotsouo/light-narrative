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

    extract_setting_topics,

    extract_unique_item_from_rule,

    is_likely_world_rule,

    is_meta_sentence,

    is_unique_item_rule,

    is_unique_item_violation,

    is_valid_setting_topic,

    is_setting_reversal_sentence,

    is_valid_object_name,

    is_valid_person_name,

    is_valid_post_death_active_evidence,

    is_valid_resolved_holder,

    is_valid_source_evidence,

    item_name_matches,

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

        if any(k in blob for k in ("復活", "亡者", "喚回", "死者")):

            return ("world_rule_violation", "dead_cannot_resurrect")

        if any(k in blob for k in ("夜裡", "說話", "聲音", "霧鐘", "替我")):

            return ("world_rule_violation", "voice_prohibition")

        if any(k in blob for k in ("退去", "相反", "白霧")):

            return ("world_rule_violation", "night_bell_outcome")

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

    if c.conflict_type == "item_location_conflict":

        item = c.related_entities[0] if c.related_entities else ""

        return ("item_location_conflict", normalize_text(item))

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

        if not is_meta_sentence(r.rule_text)

        and any(

            k in r.rule_text

            for k in (

                "亡者不能",

                "死者",

                "不能被任何法術復活",

                "不得復活",

                "無法復活",

                "不能讓他重新說話",

                "不得喚回",

                "不能喚回",

            )

        )

    ]





def _resurrection_events(events: list[Event]) -> list[Event]:

    out: list[Event] = []

    for ev in events:

        blob = f"{ev.action} {ev.evidence}"

        if any(k in blob for k in ("復活", "喚回", "從火焰中走出", "走出火焰", "被鐘復活", "走出冷室", "从棺木")):

            if is_valid_source_evidence(ev.evidence) and not is_meta_sentence(ev.evidence):

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

    if subject and not is_valid_person_name(subject):

        subject = "角色"

    c = _make_conflict(

        project_id=project_id,

        conflict_type="world_rule_violation",

        severity="high",

        title="復活或喚回違反「死者不得重返」世界規則",

        related=[subject, "亡者"],

        claim_a="文本設定死者/亡者不得被喚回、復活或重新說話。",

        claim_b="後文事件描述角色被喚回、復活、重返或再次說話。",

        evidence_a=best_rule.evidence,

        evidence_b=best_event.evidence,

        explanation="世界觀規則禁止死者重返，但事件呈現喚回或復活的結果。",

        suggested_fix="若要允許喚回，需補充例外條件/代價/機制；否則改寫事件結果。",

        chapters=[best_rule.chapter or "", best_event.chapter or ""],

    )

    return [c] if c else []





def _unique_violation_sources(rules: list[WorldRule], events: list[Event], item: str) -> list[tuple[str, str | None]]:

    sources: list[tuple[str, str | None]] = []

    for ev in events:

        if not is_valid_source_evidence(ev.evidence) or is_meta_sentence(ev.evidence):

            continue

        if is_unique_item_violation(ev.evidence) and item_name_matches(item, ev.evidence):

            sources.append((ev.evidence, ev.chapter))

    for r in rules:

        if r.rule_text and not is_meta_sentence(r.rule_text):

            if is_unique_item_violation(r.rule_text) and item_name_matches(item, r.rule_text):

                if not is_unique_item_rule(r.rule_text):

                    sources.append((r.evidence, r.chapter))

    return sources





def rule3_unique_item(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:

    conflicts: list[ConflictReport] = []

    seen_items: set[str] = set()

    for r in rules:

        if is_meta_sentence(r.rule_text) or not is_unique_item_rule(r.rule_text):

            continue

        item = extract_unique_item_from_rule(r.rule_text)

        if not item:

            continue

        norm_item = normalize_unique_item_name(item)

        if not norm_item or norm_item in seen_items or not is_valid_object_name(norm_item):

            continue

        dup_sources = _unique_violation_sources(rules, events, norm_item)

        dup_sources = [
            src
            for src in dup_sources
            if any(
                m in src[0]
                for m in ("備用", "另一枚", "第二枚", "三枚", "多枚", "副本", "複製", "同樣的", "又出現")
            )
        ]

        if not dup_sources:

            continue

        seen_items.add(norm_item)

        ev_text, ev_chapter = dup_sources[0]

        c = _make_conflict(

            project_id=project_id,

            conflict_type="unique_item_conflict",

            severity="high",

            title=f"唯一物品「{norm_item}」出現矛盾",

            related=[norm_item],

            claim_a=f"文本宣稱「{norm_item}」具有唯一性（或唯一功能）。",

            claim_b="後文出現備用品、另一枚、副本或同功能替代品。",

            evidence_a=r.evidence,

            evidence_b=ev_text,

            explanation="先宣稱物品唯一，後續卻出現備用品或同功能替代品，可能造成設定矛盾。",

            suggested_fix="若確有多枚，請改寫「唯一」的範圍或補上來源差異；否則移除備用描述。",

            chapters=[r.chapter or "", ev_chapter or ""],

        )

        if c:

            conflicts.append(c)

    return conflicts





def _has_transfer_between(states, holder_a: str, holder_b: str) -> bool:

    for s in states:

        if not s.evidence:

            continue

        if re.search(

            rf"{re.escape(holder_a)}把.{{0,12}}(?:交給|交予|交還|遞給){re.escape(holder_b)}"

            rf"|{re.escape(holder_b)}把.{{0,12}}(?:交給|交予|交還|遞給){re.escape(holder_a)}",

            s.evidence,

        ):

            return True

    return False





def rule4_item_location_holder(item_states, project_id: str) -> list[ConflictReport]:

    conflicts: list[ConflictReport] = []

    by_item: dict[str, list] = defaultdict(list)

    for s in item_states:

        by_item[s.item].append(s)



    for item, states in by_item.items():

        if not is_valid_object_name(item):

            continue

        holders = [s for s in states if s.holder and is_valid_resolved_holder(s.holder)]

        denials = [s for s in states if s.property == "denied_holder" and s.holder and is_valid_resolved_holder(s.holder)]



        for denial in denials:

            for hold in holders:

                if denial.holder != hold.holder:

                    continue

                c = _make_conflict(

                    project_id=project_id,

                    conflict_type="item_location_conflict",

                    severity="medium",

                    title=f"物品「{item}」持有人紀錄互相矛盾",

                    related=[item, hold.holder],

                    claim_a=f"某段紀錄宣稱「{item}」從未由 {hold.holder} 持有或保管。",

                    claim_b=f"另一段紀錄卻顯示 {hold.holder} 持有或保管「{item}」。",

                    evidence_a=denial.evidence,

                    evidence_b=hold.evidence,

                    explanation="同一物品的保管紀錄互相否認，若無合理轉移或誤記說明，可能造成矛盾。",

                    suggested_fix="補上交接、誤記或不同紀錄來源的說明，或統一官方紀錄。",

                    chapters=[denial.chapter or "", hold.chapter or ""],

                )

                if c:

                    conflicts.append(c)



        unique_holders = {h.holder for h in holders}

        if len(unique_holders) <= 1:

            continue

        holder_list = holders

        a, b = holder_list[0], holder_list[-1]

        if not a.holder or not b.holder or a.holder == b.holder:

            continue

        if _has_transfer_between(states, a.holder, b.holder):

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

        if not is_meta_sentence(r.rule_text)

        and any(t in r.rule_text for t in ("夜", "夜半", "子夜", "夜裡"))

        and any(k in r.rule_text for k in ("敲鐘", "敲響", "鐘", "霧鐘", "黎明"))

    ]





def _night_bell_outcome_rules(rules: list[WorldRule]) -> list[WorldRule]:

    return [

        r

        for r in _night_bell_rules(rules)

        if any(k in r.rule_text for k in ("白霧", "黑霧", "引進", "靠近", "前進", "引來", "退回"))

    ]





def _night_bell_outcome_events(events: list[Event]) -> list[Event]:

    out: list[Event] = []

    for ev in events:

        if not is_valid_source_evidence(ev.evidence) or is_meta_sentence(ev.evidence):

            continue

        if is_likely_world_rule(ev.evidence):

            continue

        blob = f"{ev.time or ''} {ev.evidence}"

        if not any(t in blob for t in ("夜半", "子夜", "夜晚", "夜間", "夜裡")):

            continue

        if not any(k in ev.evidence for k in ("敲", "霧鐘", "鐘聲", "響")):

            continue

        if any(k in ev.evidence for k in ("退去", "退回", "相反", "沒有靠近", "沒有引進")):

            out.append(ev)

    return out





def _night_bell_events(events: list[Event]) -> list[Event]:

    out: list[Event] = []

    for ev in events:

        if not is_valid_source_evidence(ev.evidence):

            continue

        if is_likely_world_rule(ev.evidence) or is_meta_sentence(ev.evidence):

            continue

        if re.search(r"(?:從未|未曾|未在|不在|沒有|没有|從不|从不).{0,12}(?:夜|夜半|夜晚|夜間)", ev.evidence):

            continue

        time_blob = f"{ev.time or ''} {ev.evidence}"

        if any(t in time_blob for t in ("夜半", "夜晚", "夜間", "子夜", "夜裡")) and any(

            k in ev.evidence for k in ("敲鐘", "敲響", "拉下", "響起", "霧鐘")

        ):

            out.append(ev)

    return out





def rule5_night_bell(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:

    outcome_rules = _night_bell_outcome_rules(rules)

    outcome_events = _night_bell_outcome_events(events)

    if outcome_rules and outcome_events:

        best_rule = max(outcome_rules, key=lambda r: len(r.evidence))

        best_event = outcome_events[0]

        c = _make_conflict(

            project_id=project_id,

            conflict_type="world_rule_violation",

            severity="high",

            title="夜半敲鐘結果與規則預期相反",

            related=["霧鐘", "白霧"],

            claim_a="文本設定夜半敲鐘會引來或推進白霧/黑霧等後果。",

            claim_b="後文卻描述夜半敲鐘後，白霧退去、結果與規則相反。",

            evidence_a=best_rule.evidence,

            evidence_b=best_event.evidence,

            explanation="規則預期與實際結果不一致，可能是劇情反轉，也可能是影鐘/複製品等特殊機制。",

            suggested_fix="若為反轉，請補充機制說明；否則調整事件結果或規則描述。",

            chapters=[best_rule.chapter or "", best_event.chapter or ""],

        )

        if c:

            return [c]



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

        related=[x for x in related if x and (is_valid_person_name(x) or x in ("敲鐘", "夜晚", "霧鐘"))],

        claim_a="文本設定夜晚敲鐘會帶來負面後果，或僅限特定時段敲鐘。",

        claim_b="後文出現夜間敲鐘的實際行動。",

        evidence_a=best_rule.evidence,

        evidence_b=best_event.evidence,

        explanation="世界觀規則限制夜晚敲鐘，但事件描述在夜間執行敲鐘。",

        suggested_fix="若要敲鐘，需補上例外/代價/防護；或將事件時間改為允許的時段。",

        chapters=[best_rule.chapter or "", best_event.chapter or ""],

    )

    return [c] if c else []





def _voice_prohibition_rules(rules: list[WorldRule]) -> list[WorldRule]:

    return [

        r

        for r in rules

        if not is_meta_sentence(r.rule_text)

        and "不要讓" in r.rule_text

        and any(t in r.rule_text for t in ("夜", "夜裡", "夜半"))

        and any(k in r.rule_text for k in ("說話", "鐘", "霧鐘", "響"))

    ]





def _voice_violation_events(events: list[Event]) -> list[Event]:

    out: list[Event] = []

    for ev in events:

        if not is_valid_source_evidence(ev.evidence) or is_meta_sentence(ev.evidence):

            continue

        blob = ev.evidence

        if any(t in blob for t in ("夜裡", "夜間", "夜半", "鐘聲", "冷室", "霧鐘")) and any(

            k in blob for k in ("聲音", "說話", "說", "開口")

        ):

            out.append(ev)

    return out





def rule8_voice_prohibition(rules: list[WorldRule], events: list[Event], project_id: str) -> list[ConflictReport]:

    prohib_rules = _voice_prohibition_rules(rules)

    violations = _voice_violation_events(events)

    if not prohib_rules or not violations:

        return []

    best_rule = prohib_rules[0]

    best_event = violations[0]

    c = _make_conflict(

        project_id=project_id,

        conflict_type="world_rule_violation",

        severity="high",

        title="夜間鐘聲/聲音違反角色遺願或禁令",

        related=["霧鐘"],

        claim_a="文本設定不要在夜裡讓鐘聲或霧鐘代替某人說話。",

        claim_b="後文卻在夜間或鐘聲後出現該角色的聲音或說話。",

        evidence_a=best_rule.evidence,

        evidence_b=best_event.evidence,

        explanation="角色遺願或禁令與後文夜間聲音事件不一致，需確認是否為伏筆或異常現象。",

        suggested_fix="若為異象，請補充機制；否則調整夜間聲音事件的時機或來源。",

        chapters=[best_rule.chapter or "", best_event.chapter or ""],

    )

    return [c] if c else []





def _collect_profile_sentences(extraction: ExtractionResult) -> list[tuple[str | None, str, str | None]]:

    """(subject_hint, sentence, chapter) 供角色限制/能力比對。"""

    rows: list[tuple[str | None, str, str | None]] = []

    for c in extraction.characters:

        for trait in c.traits:

            if not is_meta_sentence(trait):

                rows.append((c.name, trait, None))

        if c.evidence:

            for sent in split_sentences(c.evidence):

                if not is_meta_sentence(sent):

                    rows.append((c.name, sent, None))

    for ev in extraction.events:

        if ev.evidence and is_valid_source_evidence(ev.evidence) and not is_meta_sentence(ev.evidence):

            subj = ev.subject if ev.subject and is_valid_person_name(ev.subject) else None

            rows.append((subj, ev.evidence, ev.chapter))

    return rows





def _infer_character_from_sentence(sent: str, names: list[str]) -> str | None:

    for name in sorted(names, key=len, reverse=True):

        if name in sent:

            return name

    for name in names:

        if len(name) >= 2 and name[:2] in sent:

            return name[:2] if name[:2] in names else name

    m = re.match(r"^([\u4e00-\u9fff]{2,3})", sent.strip())

    if m:

        candidate = m.group(1)

        if candidate in names and is_valid_person_name(candidate):

            return candidate

    return None





def _limitation_contradicts_behavior(lim_sent: str, act_sent: str) -> bool:

    lim = lim_sent

    act = act_sent

    combat_lim = any(k in lim for k in ("不擅", "不會", "無法", "不能", "膽小", "畏縮", "容易退縮", "害怕"))

    combat_act = any(k in act for k in COMBAT_KEYWORDS + ("擊敗", "熟練", "制服", "無畏", "衝鋒", "擊倒"))

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

    names = [c.name for c in extraction.characters if is_valid_person_name(c.name)]

    for ev in extraction.events:
        if ev.subject and is_valid_person_name(ev.subject) and ev.subject not in names:
            names.append(ev.subject)

    if not names:

        return []



    limitation_by_char: dict[str, str] = {}

    combat_by_char: dict[str, str] = {}



    for c in extraction.characters:

        if not is_valid_person_name(c.name):

            continue

        for trait in c.traits:

            if any(k in trait for k in LIMITATION_KEYWORDS) and not is_meta_sentence(trait):

                limitation_by_char.setdefault(c.name, trait)



    rows = _collect_profile_sentences(extraction)

    last_named: str | None = None

    for subj_hint, sent, _chapter in rows:

        if is_meta_sentence(sent):

            continue

        name = subj_hint if subj_hint and is_valid_person_name(subj_hint) else None

        if not name:

            name = _infer_character_from_sentence(sent, names)

        if name and is_valid_person_name(name):

            last_named = name

        if any(k in sent for k in LIMITATION_KEYWORDS):

            who = name or last_named

            if who and who in names and is_valid_person_name(who) and who in sent:

                limitation_by_char.setdefault(who, sent)

        if any(k in sent for k in HIGH_ABILITY_KEYWORDS):

            who = name

            if not who and sent.strip().startswith(("她", "他")) and last_named:

                who = last_named

            if not who:

                who = _infer_character_from_sentence(sent, names)

            if who and who in names and is_valid_person_name(who):

                lim = limitation_by_char.get(who)

                if lim and _limitation_contradicts_behavior(lim, sent):

                    combat_by_char.setdefault(who, sent)



    for name, lim_ev in limitation_by_char.items():

        if not is_valid_person_name(name):

            continue

        combat_ev = combat_by_char.get(name)

        if not combat_ev or name not in lim_ev:

            continue

        if name not in combat_ev and not combat_ev.strip().startswith(("她", "他")):

            continue

        if not _limitation_contradicts_behavior(lim_ev, combat_ev):

            continue

        if not any(k in combat_ev for k in HIGH_ABILITY_KEYWORDS):

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

    usable_rules = [r for r in rules if not is_meta_sentence(r.rule_text)]

    early_rules = [
        r
        for r in usable_rules
        if extract_setting_topics(r.rule_text)
        and any(
            k in r.rule_text
            for k in ("維持", "维持", "界線", "界线", "中央", "位於", "位于", "黑石牆", "市政廳", "舊檔案", "公開", "所有人都知道")
        )
    ]

    late_rules = [
        r
        for r in usable_rules
        if is_setting_reversal_sentence(r.rule_text)
        and (
            extract_setting_topics(r.rule_text)
            or any(k in r.rule_text for k in ("密令", "影鐘", "複製品", "複製", "真相"))
        )
    ]

    seen_late: set[str] = set()

    bs_early = [
        r
        for r in early_rules
        if "黑石牆" in r.rule_text
        and any(k in r.rule_text for k in ("市政廳", "刻", "公開", "舊檔案", "所有人都知道"))
    ]
    bs_late = [
        r
        for r in late_rules
        if "密令" in r.rule_text and any(k in r.rule_text for k in ("影鐘", "複製", "真相", "不得", "秘密"))
    ]
    if bs_early and bs_late:
        early = bs_early[0]
        late = max(bs_late, key=lambda r: sum(k in r.rule_text for k in ("影鐘", "複製", "密令", "真相")))
        c = _make_conflict(
            project_id=project_id,
            conflict_type="world_setting_conflict",
            severity="medium",
            title="「黑石牆」相關世界設定出現重大反轉",
            related=["黑石牆"],
            claim_a="前文建立的核心設定、公開規則或檔案描述。",
            claim_b="後文揭示設定被推翻、秘密揭露、影鐘/複製或偽裝真相。",
            evidence_a=early.evidence,
            evidence_b=late.evidence,
            explanation="這可能是劇情反轉，不一定是錯誤，但屬於重大設定變更，需要作者確認是否已鋪陳伏筆。",
            suggested_fix="在反轉前加入暗示，或在反轉當下補充可信的因果與資訊來源。",
            chapters=[early.chapter or "", late.chapter or ""],
        )
        if c:
            conflicts.append(c)
            seen_late.add(late.evidence)

    for late in late_rules:

        if late.evidence in seen_late:

            continue

        best_early: WorldRule | None = None

        best_ent = ""

        best_score = -1

        for early in early_rules:

            if early.evidence == late.evidence:

                continue

            early_topics = {t for t in extract_setting_topics(early.rule_text) if is_valid_setting_topic(t)}

            if not early_topics:

                continue

            late_topics = {t for t in extract_setting_topics(late.rule_text) if is_valid_setting_topic(t)}

            shared = early_topics & late_topics

            if not shared:

                overlap = {t for t in early_topics if t in late.rule_text}

                if overlap:

                    shared = overlap

            if not shared:

                if "黑石牆" in early.rule_text and any(
                    k in late.rule_text for k in ("密令", "影鐘", "複製", "真相")
                ):
                    shared = {"黑石牆"}

                else:

                    continue

            ent = max(shared, key=len)

            score = len(shared) * 10 + len(ent)

            if "黑石牆" in early.rule_text and any(
                k in late.rule_text for k in ("密令", "影鐘", "複製", "真相")
            ):
                score += 100

            if score > best_score:

                best_score = score

                best_early = early

                best_ent = ent

        if not best_early or not best_ent:

            continue

        seen_late.add(late.evidence)

        c = _make_conflict(

            project_id=project_id,

            conflict_type="world_setting_conflict",

            severity="medium",

            title=f"「{best_ent}」相關世界設定出現重大反轉",

            related=[best_ent],

            claim_a="前文建立的核心設定、公開規則或檔案描述。",

            claim_b="後文揭示設定被推翻、秘密揭露、影鐘/複製或偽裝真相。",

            evidence_a=best_early.evidence,

            evidence_b=late.evidence,

            explanation="這可能是劇情反轉，不一定是錯誤，但屬於重大設定變更，需要作者確認是否已鋪陳伏筆。",

            suggested_fix="在反轉前加入暗示，或在反轉當下補充可信的因果與資訊來源。",

            chapters=[best_early.chapter or "", late.chapter or ""],

        )

        if c:

            conflicts.append(c)

    return _prune_world_setting_conflicts(conflicts)


def _prune_world_setting_conflicts(conflicts: list[ConflictReport]) -> list[ConflictReport]:
    setting = [c for c in conflicts if c.conflict_type == "world_setting_conflict"]
    other = [c for c in conflicts if c.conflict_type != "world_setting_conflict"]
    if len(setting) <= 2:
        return conflicts
    ranked = sorted(setting, key=lambda c: (-len(c.related_entities[0]), c.title))
    kept: list[ConflictReport] = []
    seen_evidence_b: set[str] = set()
    for c in ranked:
        ent = c.related_entities[0] if c.related_entities else ""
        if not ent:
            continue
        if c.evidence_b in seen_evidence_b:
            continue
        if any(
            ent != k.related_entities[0]
            and (ent in k.related_entities[0] or k.related_entities[0] in ent)
            for k in kept
        ):
            continue
        kept.append(c)
        seen_evidence_b.add(c.evidence_b)
        if len(kept) >= 2:
            break
    # 保留黑石牆與其他主題各一筆（若存在）
    if not any(k.related_entities and k.related_entities[0] == "黑石牆" for k in kept):
        for c in ranked:
            if c.related_entities and c.related_entities[0] == "黑石牆" and c.evidence_b not in seen_evidence_b:
                kept.append(c)
                break
    return other + kept[:3]





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

    conflicts.extend(rule8_voice_prohibition(extraction.world_rules, extraction.events, project_id))

    conflicts.extend(rule6_character_drift(extraction, project_id))

    conflicts.extend(rule7_world_setting(extraction.world_rules, project_id))



    conflicts = _dedupe_merge([c for c in conflicts if c is not None])



    severity_order = {"high": 0, "medium": 1, "low": 2}

    conflicts.sort(key=lambda c: severity_order.get(c.severity, 9))

    return conflicts

