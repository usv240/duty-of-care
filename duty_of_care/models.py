from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Scene(BaseModel):
    scene_id: str
    heading: str
    text: str


class Trigger(BaseModel):
    scene_id: str
    trigger_class: Literal[
        "method_specificity",
        "framing_as_solution",
        "absence_of_help_seeking",
        "romanticisation",
        "repetition",
        "signposting_absence",
    ]
    evidence_excerpt: str
    rule: str


class GuidanceClause(BaseModel):
    clause_id: str = ""
    jurisdiction: str
    publisher: str
    document_title: str
    clause: str
    source_url: str
    trigger_classes: list[str] = Field(default_factory=list)
    version: str = ""
    retrieved_at: str = ""


class ReviewRequest(BaseModel):
    screenplay: str = Field(min_length=1, max_length=250_000)
    region: str = Field(default="US", max_length=8)


class Suggestion(BaseModel):
    original: str
    proposed: str
    dramatic_intent: str
