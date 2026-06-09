"""Pydantic 結構化 schema。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid4())


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictType(str, Enum):
    CHARACTER_STATE = "character_state"
    ITEM_LOCATION = "item_location"
    TIMELINE = "timeline"
    WORLD_RULE = "world_rule"
    CHARACTER_DRIFT = "character_drift"


class Project(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    filename: str
    raw_text: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    id: str = Field(default_factory=_new_id)
    document_id: str
    project_id: str
    # index: chunk 在整份文件中的順序（0-based）
    index: int

    # chapter_index: 章節序號（若可解析則為 0..n；否則退化為 index）
    chapter_index: int = 0
    chapter_title: str = ""
    text: str
    kind: str = "scene"  # chapter | scene | chunk
    start_char: int = 0
    end_char: int = 0


class Character(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    name: str
    traits: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    states: list[dict[str, Any]] = Field(default_factory=list)
    source_chunk_id: str | None = None
    evidence: str = ""


class Location(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    name: str
    description: str = ""
    source_chunk_id: str | None = None
    evidence: str = ""


class StoryObject(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    name: str
    location: str | None = None
    owner: str | None = None
    source_chunk_id: str | None = None
    evidence: str = ""


class Event(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    subject: str | None = None
    action: str
    object: str | None = None
    location: str | None = None
    time: str | None = None
    result: str | None = None
    chapter: str | None = None
    chunk_id: str
    evidence: str


class WorldRule(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    rule_text: str
    subject: str | None = None
    constraint: str | None = None
    condition: str | None = None
    exception: str | None = None
    chapter: str | None = None
    chunk_id: str
    evidence: str


class CharacterState(BaseModel):
    character: str
    state: Literal["alive", "dead", "active", "buried", "resurrected", "unknown"]
    chapter: str | None = None
    chunk_id: str
    evidence: str


class ItemState(BaseModel):
    item: str
    holder: str | None = None
    location: str | None = None
    property: str | None = None
    chapter: str | None = None
    chunk_id: str
    evidence: str


class ExtractionResult(BaseModel):
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    objects: list[StoryObject] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    world_rules: list[WorldRule] = Field(default_factory=list)
    character_states: list[CharacterState] = Field(default_factory=list)
    item_states: list[ItemState] = Field(default_factory=list)


class ConflictReport(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    conflict_type: Literal[
        "world_rule_violation",
        "character_state_conflict",
        "unique_item_conflict",
        "item_location_conflict",
        "character_consistency_drift",
        "world_setting_conflict",
    ]
    severity: Literal["low", "medium", "high"]
    title: str
    related_entities: list[str] = Field(default_factory=list)
    claim_a: str
    claim_b: str
    evidence_a: str
    evidence_b: str
    explanation: str
    suggested_fix: str = ""
    chapters: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    project_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = 0
    entity_counts: dict[str, int] = Field(default_factory=dict)
    conflict_counts: dict[str, int] = Field(default_factory=dict)
    conflicts: list[ConflictReport] = Field(default_factory=list)
