"""事件抽取（排除世界觀規則句）。"""
from __future__ import annotations

import re

from src.llm_client import BaseLLMProvider
from src.narrative_patterns import (
    EVENT_ACTION_KEYWORDS,
    is_likely_event,
    is_valid_person_name,
    split_sentences,
)
from src.schemas import Chunk, Event
from src.utils import safe_json_loads

EVENT_SYSTEM = """你是敘事分析助手。從文本抽取事件，JSON 格式：
{
  "events": [
    {
      "subject": null,
      "action": "",
      "object": null,
      "location": null,
      "time": null,
      "result": null,
      "evidence": ""
    }
  ]
}
只輸出 JSON，不虛構。不要輸出世界觀規則句。"""


def _guess_time_label(text: str) -> str | None:
    m = re.search(r"(夜半|夜晚|清晨|黃昏|翌日|同時|黎明)", text)
    return m.group(1) if m else None


def _infer_action(sent: str) -> str:
    for k in EVENT_ACTION_KEYWORDS:
        if k in sent:
            return k
    return "發生"


def _infer_subject(sent: str) -> str | None:
    m = re.match(r"^([\u4e00-\u9fff]{2})(?=[，,、\s在將把]|[^一-龥]|$)", sent)
    if m and is_valid_person_name(m.group(1)):
        return m.group(1)
    m2 = re.search(r"^([\u4e00-\u9fff]{2})(?:拉下|敲響|走出|走進|命令|把|在)", sent)
    if m2 and is_valid_person_name(m2.group(1)):
        return m2.group(1)
    return None


def _infer_object(sent: str) -> str | None:
    m = re.search(r"([\u4e00-\u9fff]{1,8}(?:鑰匙|鐘|劍|刀|門|守衛|黑霧))", sent)
    return m.group(1) if m else None


def extract_events_heuristic(chunk: Chunk) -> list[Event]:
    events: list[Event] = []
    for sent in split_sentences(chunk.text):
        if not is_likely_event(sent):
            continue
        events.append(
            Event(
                project_id=chunk.project_id,
                subject=_infer_subject(sent),
                action=_infer_action(sent),
                object=_infer_object(sent),
                location=None,
                time=_guess_time_label(sent),
                result=None,
                chapter=chunk.chapter_title or None,
                chunk_id=chunk.id,
                evidence=sent,
            )
        )
    return events[:40]


def extract_events_llm(chunk: Chunk, llm: BaseLLMProvider) -> list[Event]:
    prompt = f"標題：{chunk.chapter_title}\n\n文本：\n{chunk.text[:3000]}"
    raw = llm.complete(prompt, system=EVENT_SYSTEM)
    data = safe_json_loads(raw)
    if not isinstance(data, dict):
        return extract_events_heuristic(chunk)

    events: list[Event] = []
    for item in data.get("events", []):
        evidence = (item.get("evidence") or item.get("action") or "").strip()
        if not is_likely_event(evidence):
            continue
        events.append(
            Event(
                project_id=chunk.project_id,
                subject=item.get("subject"),
                action=item.get("action") or _infer_action(evidence),
                object=item.get("object"),
                location=item.get("location"),
                time=item.get("time"),
                result=item.get("result"),
                chapter=chunk.chapter_title or None,
                chunk_id=chunk.id,
                evidence=evidence,
            )
        )
    return events


def attach_events(extraction, events: list[Event]):
    extraction.events = events
    return extraction
