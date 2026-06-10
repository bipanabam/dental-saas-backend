"""
Shared dataclasses used across all taxonomy modules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

MedicalHistoryType = Literal["critical", "warning", "info"]
ExamFieldType      = Literal["checkbox", "text", "select"]


@dataclass(frozen=True)
class MedicalHistoryItem:
    id:    str
    label: str
    type:  MedicalHistoryType


@dataclass(frozen=True)
class ExamField:
    id:      str
    label:   str
    type:    ExamFieldType
    # only populated for type="select"
    options: tuple[str, ...] = field(default_factory=tuple)