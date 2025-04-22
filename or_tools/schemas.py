#Not into the database, just used for fastapi through python

from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class FixedTask(BaseModel):
    id: str
    start: datetime
    end: datetime
    priority: int
    dependencies: List[str] = []

class FlexibleTask(BaseModel):
    id: str
    total_hours: int
    session_hours: int
    deadline: datetime
    priority: int
    dependencies: List[str] = []
    max_per_day: Optional[int] = None

class ScheduleRequest(BaseModel):
    week_start: datetime
    fixed_tasks: List[FixedTask]
    flexible_tasks: List[FlexibleTask]

class CalendarEventResponse(BaseModel):
    id: str
    start_time: datetime
    end_time: datetime
    type: str

class UpdateRequest(BaseModel):
    old_events: List[CalendarEventResponse]
    new_tasks: ScheduleRequest