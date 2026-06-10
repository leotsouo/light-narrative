"""通用敘事文本 pattern（不硬編特定作品人名/物品）。"""
from __future__ import annotations

import re

from src.utils import normalize_text

# 非人名詞（時間副詞、序號、常見誤抽）
NON_PERSON_WORDS: frozenset[str] = frozenset(
    {
        "立刻",
        "突然",
        "半小時後",
        "幾分鐘後",
        "同一天晚上",
        "隔天清晨",
        "黃昏時分",
        "午夜時",
        "黎明前兩小時",
        "第一",
        "第二",
        "第三",
        "第四",
        "第五",
        "第六",
        "第七",
        "第八",
        "第九",
        "第十",
        "然而",
        "因此",
        "於是",
        "接著",
        "隨後",
        "此時",
        "當時",
        "眾人",
        "眾人",
        "有人",
        "眾",
        "清晨",
        "翌日",
        "後山",
        "同時",
        "傳聞",
        "鎮上",
        "當夜",
        "這件",
        "這段",
        "這次",
        "這些",
        "那些",
        "她把",
        "他說",
        "她說",
        "他們",
        "自己",
        "後來",
        "前面",
        "這一章",
        "守衛",
        "這一",
        "那一",
    }
)

INVALID_CHARACTER_SUFFIXES: frozenset[str] = frozenset({"把", "說", "段", "件", "們", "時", "後"})
INVALID_CHARACTER_PREFIXES: frozenset[str] = frozenset({"這", "那", "他", "她", "它"})

UNIQUE_ITEM_RULE_MARKERS = (
    "唯一",
    "只有一枚",
    "只有一個",
    "沒有備用",
    "沒有副本",
    "沒有第二枚",
    "不得複製",
    "任何人不得複製",
)
UNIQUE_ITEM_VIOLATION_MARKERS = (
    "備用",
    "備用品",
    "另一枚",
    "第二枚",
    "三枚",
    "多枚",
    "副本",
    "複製品",
    "秘密複製",
    "複製計畫",
    "又出現",
    "外形相同",
    "同樣的",
)
META_SENTENCE_MARKERS = (
    "若它抓到",
    "檢查表",
    "答案比對",
    "應能在",
    "代表核心規則",
    "改名為",
    "學期展示",
    "期末摘要",
    "高風險詞",
    "不一定構成",
    "這些段落",
)
SETTING_EARLY_KEYWORDS = (
    "維持",
    "维持",
    "位於",
    "位于",
    "中央",
    "每天",
    "界線",
    "界线",
    "規則",
    "设定",
    "設定",
    "所有人都知道",
    "舊檔案",
    "公開",
    "黑石牆",
    "市政廳",
)
SETTING_REVERSAL_KEYWORDS = (
    "真正的",
    "移到",
    "複製品",
    "复制品",
    "不在",
    "早已",
    "其實",
    "其实",
    "實際上",
    "并非",
    "並非",
    "密令",
    "秘密",
    "不得公開",
    "複製計畫",
    "只是",
    "不得被稱為",
    "真相",
)

# holder/location 無效片段
INVALID_HOLDER_LOCATION: frozenset[str] = frozenset(
    {
        "艱難地說",
        "因為",
        "黎明",
        "第一",
        "第二",
        "被敲",
        "敲響",
        "確認",
        "發現",
        "自己",
    }
)

INVALID_OBJECT_PREFIXES: frozenset[str] = frozenset(
    {
        "下",
        "色",
        "響",
        "塔",
        "錨",
        "枚",
        "全",
        "的",
        "門",
        "城",
        "晚",
        "半",
        "一",
        "能",
        "打",
        "開",
        "此",
        "這",
        "該",
        "內",
        "外",
        "著",
        "後",
        "稱",
        "密",
        "正正",
    }
)
INVALID_OBJECT_NAMES: frozenset[str] = frozenset({"密令", "政令", "口令", "檢員"})
PERSON_NAME = r"[\u4e00-\u9fff]{2}"  # 主體角色名（2 字）用於狀態/行動句，避免「羅恩從她」誤抽

LIMITATION_KEYWORDS = ("害怕", "不擅", "膽小", "畏縮", "容易退縮", "不敢", "不擅長", "不會", "無法", "不能")
COMBAT_KEYWORDS = ("徒手擊倒", "擊倒", "動作熟練", "像訓練多年", "一招制敵", "制服")
HIGH_ABILITY_KEYWORDS = COMBAT_KEYWORDS + (
    "擊敗",
    "熟練",
    "輕易",
    "成功使用",
    "突然能",
    "毫不畏懼",
    "無畏",
)

ITEM_NOUN_RE = r"[\u4e00-\u9fff]{1,8}(?:鑰匙|劍|刀|符|印|寶石|玉佩|信物|鐘|令)"
DEMONSTRATIVE_ITEMS: frozenset[str] = frozenset({"這", "此", "該", "這個", "這把", "這件", "這項"})

# 死亡後仍活動：須為明確行動句，排除倒地/遺體等
POST_DEATH_INACTIVE_RE = re.compile(
    rf"({PERSON_NAME})(?:[^。]{{0,12}})?(?:倒在|逝世|身亡|遇害|停止呼吸|"
    rf"的遺體|的棺木|已經死亡|確認[^。]{{0,8}}死亡)"
)
POST_DEATH_ACTIVE_RE = re.compile(
    rf"({PERSON_NAME})(?:[^。]{{0,20}})?(?:"
    rf"說|告訴|回答|走|站|衝|攻擊|使用|要求|出現|扶著|進入|命令|"
    rf"身後說|說道|笑道|問道|喊道|走出|現身|從[^。]{{0,12}}走出|拉下|敲響|敲鐘|擊倒|打開)"
)

UNIQUE_ITEM_RE = re.compile(
    rf"({ITEM_NOUN_RE})是[^。]{{0,30}}唯一|唯一[^。]{{0,30}}的({ITEM_NOUN_RE})",
)
OBSERVER_DEATH_RE = re.compile(
    rf"({PERSON_NAME})(?:確認|看見|發現|知道).{{0,8}}(?:他|她).{{0,12}}(?:已經)?死亡"
)
DEAD_SUBJECT_RE = [
    re.compile(rf"({PERSON_NAME})(?:停止呼吸|已經死亡|死了|逝世)"),
    re.compile(rf"({PERSON_NAME})(?:在[^。]{{0,24}})?(?:遇害|身亡)"),
    re.compile(rf"({PERSON_NAME})的(?:遺體|棺木)"),
    re.compile(rf"({PERSON_NAME})(?:被)?(?:安葬|下葬|埋葬)"),
]
PASSIVE_ACTIVE_RE = re.compile(
    rf"(?:看見|見到|發現)({PERSON_NAME})(?![^。]{{0,8}}倒在)"
    rf"|({PERSON_NAME})[^。]{{0,30}}(?:說笑|買藥|進入)"
)
RESURRECT_SUBJECT_RE = re.compile(
    rf"({PERSON_NAME}).{{0,20}}(?:復活|從火焰中走出|走出火焰|醒來)"
)
ACTIVE_SUBJECT_RE = re.compile(
    rf"^({PERSON_NAME})(?:從[^。]{{0,8}})?(?:身後說|說道|笑道|問道|喊道|"
    rf"走進|走出|出現|現身|命令|打開|拉下|敲響|敲鐘|擊倒|制服|進入|說笑)"
)

RULE_LIKE_RE = re.compile(
    r"(不能|不得|禁止|唯一|維持|規則|設定|自古|必須|只能在|第[一二三四五六七八九十]+[，,])"
)
EVENT_ACTION_KEYWORDS = (
    "拉下",
    "敲響",
    "響起",
    "交給",
    "交還",
    "走出",
    "走進",
    "進入",
    "停止呼吸",
    "復活",
    "擊倒",
    "打開",
    "命令",
    "藏進",
    "拿出",
    "身後說",
    "說道",
    "說笑",
    "笑道",
    "衝鋒",
    "無畏",
    "買藥",
    "備用",
    "出現",
    "拍賣會",
)


def is_meta_sentence(text: str) -> bool:
    return any(marker in text for marker in META_SENTENCE_MARKERS)


def is_unique_item_rule(text: str) -> bool:
    return any(marker in text for marker in UNIQUE_ITEM_RULE_MARKERS)


def is_unique_item_violation(text: str) -> bool:
    negations = ("從未", "沒有", "不曾", "未出現", "未會", "並無", "不得有", "無備用", "無副本")
    for marker in UNIQUE_ITEM_VIOLATION_MARKERS:
        idx = text.find(marker)
        if idx == -1:
            continue
        prefix = text[max(0, idx - 10):idx]
        if any(neg in prefix for neg in negations):
            continue
        if re.search(rf"(?:從未|沒有|無|未|不得).{{0,8}}{re.escape(marker)}", text):
            continue
        return True
    return False


def item_name_matches(item: str, text: str) -> bool:
    if not item or not text:
        return False
    if item in text:
        return True
    for suf in ("鑰匙", "令", "印", "印信"):
        if not item.endswith(suf):
            continue
        prefix = item[: -len(suf)]
        if suf not in text:
            continue
        if prefix and prefix in text:
            return True
        if any(
            m in text
            for m in ("備用", "另一把", "另一枚", "第二把", "第二枚", "三枚", "副本", "複製", "同樣的", "又出現")
        ):
            return True
    return False


def extract_setting_topics(text: str) -> set[str]:
    topics: set[str] = set()
    for kw in ("黑石牆", "市政廳", "影鐘", "正鐘", "鹽墓", "北塔", "北塔霧鐘"):
        if kw in text:
            topics.add(kw)
    if "霧鐘" in text:
        topics.add("霧鐘")
    m = re.search(r"[「『]([^」』]{2,10})[」』]", text)
    if m:
        ent = m.group(1).strip()
        if len(ent) >= 2 and not ent.startswith(("若", "第", "這")):
            topics.add(ent)
    for name in extract_object_names_from_text(text):
        topics.add(name)
    return topics


def is_setting_reversal_sentence(text: str) -> bool:
    strong_markers = (
        "複製品",
        "影鐘",
        "密令",
        "真正的",
        "真相",
        "其實",
        "只是複製",
        "被移到",
        "並非",
        "不是真正",
        "不得被稱為",
        "複製計畫",
    )
    if not any(k in text for k in strong_markers):
        return False
    if any(neg in text for neg in ("未揭示", "沒有反轉", "並無反轉", "未出現反轉")):
        return False
    if re.search(r"(?:未|沒有|無|不曾).{0,8}(?:複製|副本|影鐘|真相)", text):
        return False
    return True


def is_valid_person_name(name: str) -> bool:
    if not name or len(name) not in (2, 3):
        return False
    if name in NON_PERSON_WORDS:
        return False
    if name[0] in INVALID_CHARACTER_PREFIXES:
        return False
    if name[-1] in INVALID_CHARACTER_SUFFIXES:
        return False
    if name.endswith(("地", "的", "了", "著", "過")):
        return False
    if re.match(r"^[一二三四五六七八九十零\d]+$", name):
        return False
    # 排除動詞/狀態詞被誤抽為人名
    if any(
        p in name
        for p in ("停止", "呼吸", "確認", "身後", "已經", "死亡", "復活", "安葬", "敲鐘", "聰明", "謹慎", "善良", "勇敢")
    ):
        return False
    return True


def filter_person_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        n = n.strip()
        if not is_valid_person_name(n) or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？\n])", text)
    return [p.strip() for p in parts if p.strip()]


def is_likely_world_rule(sentence: str) -> bool:
    s = sentence.strip()
    if len(s) < 6:
        return False
    if is_meta_sentence(s):
        return False
    # 含明確動作動詞的句子優先視為 Event
    if any(k in s for k in ("拉下", "敲響", "響起", "走出", "走進", "停止呼吸", "交給", "交還", "擊倒")):
        return False
    if RULE_LIKE_RE.search(s):
        return True
    if "世界觀" in s or "設定" in s:
        return True
    if "唯一" in s:
        return True
    if ("夜" in s or "黎明" in s) and ("鐘" in s or "敲" in s):
        return True
    if "維持" in s and ("界線" in s or "外界" in s):
        return True
    if any(k in s for k in SETTING_REVERSAL_KEYWORDS):
        return True
    return False


def is_likely_event(sentence: str) -> bool:
    s = sentence.strip()
    if len(s) < 5:
        return False
    if is_likely_world_rule(s):
        return False
    if not any(k in s for k in EVENT_ACTION_KEYWORDS):
        return False
    # 排除純規則敘述（無主體行動）
    if re.match(r"^第[一二三四五六七八九十]+[，,]", s):
        return False
    return True


def normalize_unique_item_name(raw: str) -> str:
    """將唯一物品名稱正規化，過濾指示代詞與整句誤抽。"""
    text = normalize_text(raw).strip()
    if not text or text in DEMONSTRATIVE_ITEMS:
        return ""
    if len(text) > 12:
        text = text[:12]

    m_said = re.match(rf"^({ITEM_NOUN_RE})被說成", text)
    if m_said:
        text = m_said.group(1).strip()

    if text in DEMONSTRATIVE_ITEMS or "被說成" in text or "唯一" in text:
        found = re.findall(rf"({ITEM_NOUN_RE})", raw)
        candidates = [c for c in found if c not in DEMONSTRATIVE_ITEMS and len(c) >= 2]
        if candidates:
            text = candidates[-1]
        else:
            return ""

    if len(text) < 2 or text in DEMONSTRATIVE_ITEMS:
        return ""
    if any(bad in text for bad in ("被說成", "唯一能", "地下", "打開")):
        m_tail = re.search(rf"的({ITEM_NOUN_RE})$", raw)
        if m_tail and m_tail.group(1) not in DEMONSTRATIVE_ITEMS:
            return m_tail.group(1).strip()
        return ""
    return text


def extract_unique_item_from_rule(rule_text: str) -> str | None:
    if not is_unique_item_rule(rule_text):
        return None
    m_quote = re.search(r"[「『]([^」』]{2,8})[」』]", rule_text)
    if m_quote:
        name = normalize_unique_item_name(m_quote.group(1))
        if name:
            return name
    tails = re.findall(rf"的({ITEM_NOUN_RE})(?:[。，,]|$)", rule_text)
    for candidate in reversed(tails):
        name = normalize_unique_item_name(candidate)
        if name:
            return name
    m_said = re.search(rf"({ITEM_NOUN_RE})被說成[^。]{{0,12}}唯一", rule_text)
    if m_said:
        name = normalize_unique_item_name(m_said.group(1))
        if name:
            return name
    m = UNIQUE_ITEM_RE.search(rule_text)
    if m:
        raw = m.group(1) or m.group(2)
        name = normalize_unique_item_name(raw)
        if name:
            return name
    found = re.findall(rf"({ITEM_NOUN_RE})", rule_text)
    for candidate in reversed(found):
        name = normalize_unique_item_name(candidate)
        if name:
            return name
    return None


def is_valid_post_death_active_evidence(character: str, sentence: str) -> bool:
    """死亡後活動證據：須含角色且為行動句，排除倒地/死亡描述。"""
    if not character or character not in sentence:
        return False
    if not is_valid_source_evidence(sentence):
        return False
    if POST_DEATH_INACTIVE_RE.search(sentence):
        return False
    if re.search(rf"(?:看見|見到|發現){character}[^。]{{0,12}}倒在", sentence):
        return False
    return bool(POST_DEATH_ACTIVE_RE.search(sentence))


def choose_more_specific_entity(entity: str, entities: list[str]) -> str:
    """若 A 為 B 子字串且 B 更具體，保留較長者；合併後仍為 1 字則捨棄。"""
    if not entity:
        return ""
    best = entity
    for other in entities:
        if other == entity:
            continue
        if len(other) > len(best) and entity in other:
            best = other
    return best if len(best) >= 2 else ""


def canonicalize_setting_entity(entity: str, all_entities: list[str]) -> str:
    chosen = choose_more_specific_entity(entity, all_entities)
    if chosen:
        return chosen
    return entity if entity and len(entity) >= 2 else ""


def extract_setting_entity(text: str) -> str | None:
    m = re.search(r"[「『]([^」』]{2,10})[」』]", text)
    if m:
        return m.group(1).strip()
    m2 = re.search(rf"(?:真正的)?({PERSON_NAME})(?:早在|位於|被移|維持|是)", text)
    if m2:
        return m2.group(1).strip()
    m3 = re.search(rf"({PERSON_NAME})(?:位於|維持)", text)
    if m3:
        return m3.group(1).strip()
    m4 = re.search(rf"({PERSON_NAME})(?:在)(?!.{0,2}早)", text)
    return m4.group(1).strip() if m4 else None


def is_valid_source_evidence(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return False
    if "相關描述" in text:
        return False
    return True


def is_valid_object_name(name: str) -> bool:
    """過濾誤抽的整句片段或指示代詞物品名。"""
    text = normalize_text(name).strip()
    if not text or len(text) < 2 or len(text) > 6:
        return False
    if text in DEMONSTRATIVE_ITEMS:
        return False
    if text in INVALID_OBJECT_NAMES:
        return False
    if text.startswith(("此", "這", "該", "真正", "城內", "讓", "一能", "稱")):
        return False
    if any(
        bad in text
        for bad in (
            "發現",
            "同時",
            "一把",
            "這是",
            "出現",
            "被說",
            "聲稱",
            "不得",
            "談論",
            "唯一",
            "能打",
            "地下",
            "打開",
            "交給",
            "掛在",
            "把",
            "握",
            "拉下",
            "讓",
            "敲",
            "真正",
            "城中",
            "手中",
            "室",
            "的",
            "大門",
            "枚",
        )
    ):
        return False
    if re.match(r"^[\u4e00-\u9fff]{1,4}(?:鑰匙|劍|刀|書|信|藥|符|玉佩|印|寶石|玉|令)$", text):
        prefix = re.sub(r"(?:鑰匙|劍|刀|書|信|藥|符|玉佩|印|寶石|玉)$", "", text)
        if prefix in INVALID_OBJECT_PREFIXES or any(x in prefix for x in ("色", "著", "後")):
            return False
        return True
    if re.match(r"^[\u4e00-\u9fff]{1,2}鐘$", text):
        prefix = text[:-1]
        if prefix in INVALID_OBJECT_PREFIXES or any(x in prefix for x in ("色", "著", "後", "下", "響")):
            return False
        return True
    return False


def is_valid_setting_topic(topic: str) -> bool:
    if not topic or len(topic) < 2 or len(topic) > 8:
        return False
    if topic in NON_PERSON_WORDS or topic in INVALID_HOLDER_LOCATION:
        return False
    if topic.startswith(("是", "被", "在", "能", "令", "不", "的", "有", "沒")):
        return False
    if any(k in topic for k in ("鐘", "令", "牆", "墓", "塔", "鹽", "霧", "市政", "黑石", "影")):
        return True
    if is_valid_object_name(topic):
        return True
    return len(topic) >= 3


def extract_object_names_from_text(text: str) -> list[str]:
    """從文本中抽取合法物品名，避免整句誤抽。"""
    found: set[str] = set()
    suffixes = ("鑰匙", "劍", "刀", "書", "信", "藥", "符", "玉佩", "印", "寶石", "玉", "鐘", "令")
    for suffix in suffixes:
        max_prefix = 2 if suffix == "鐘" else 4
        for m in re.finditer(re.escape(suffix), text):
            idx = m.start()
            for plen in range(1, max_prefix + 1):
                if idx - plen < 0:
                    continue
                prefix = text[idx - plen : idx]
                if not re.fullmatch(r"[\u4e00-\u9fff]+", prefix):
                    continue
                name = prefix + suffix
                if is_valid_object_name(name):
                    found.add(name)
    keep: list[str] = []
    for name in sorted(found, key=len, reverse=True):
        if any(name != other and name in other for other in keep):
            continue
        keep.append(name)
    return keep


def is_valid_resolved_holder(holder: str | None) -> bool:
    """物品持有人須為具體人名，不接受代名詞或未解析的「自己」。"""
    if not holder:
        return False
    h = holder.strip()
    if h in INVALID_HOLDER_LOCATION or h in DEMONSTRATIVE_ITEMS:
        return False
    if h in ("自己", "她", "他", "它", "這", "此", "該"):
        return False
    return is_valid_person_name(h)


def is_valid_holder_or_location(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    if v in INVALID_HOLDER_LOCATION or v in NON_PERSON_WORDS:
        return False
    if any(bad in v for bad in ("地說", "因為", "被敲", "敲響", "黎明")):
        return False
    if len(v) < 2 or len(v) > 8:
        return False
    return True
