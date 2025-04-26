from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FixedTask(BaseModel):
    id: str
    start: datetime
    end: datetime
    priority: int = 1


class FlexibleTask(BaseModel):
    id: str
    total_hours: int = Field(..., ge=1)
    session_hours: int = Field(..., ge=1)
    deadline: datetime
    priority: int = 5
    dependencies: List[str] = []
    max_per_day: Optional[int] = None  # future use


class AcademicTask(FlexibleTask):
    """Same fields – separate class just for typing clarity."""
    pass


class Preferences(BaseModel):
    peak_hours: List[int] = []
    max_hours_per_day: int = 6
    min_gap_between_sessions: int = 1


class GenerateRequest(BaseModel):
    week_start: datetime
    fixed_tasks: List[FixedTask] = []
    flexible_tasks: List[FlexibleTask] = []
    academic_tasks: List[AcademicTask] = []
    preferences: Optional[Preferences] = None


class CalendarEvent(BaseModel):
    id: str
    start_time: datetime
    end_time: datetime
    type: str
    parent_task_id: Optional[str] = None


class UpdateRequest(BaseModel):
    old_events: List[CalendarEvent]
    new_payload: GenerateRequest