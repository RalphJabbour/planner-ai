from fastapi import APIRouter
from .schemas import ScheduleRequest, UpdateRequest, CalendarEventResponse
from .service import generate_schedule_from_request, update_schedule_from_request
from typing import List

router = APIRouter(prefix="/schedule", tags=["Scheduler"])

@router.post("/generate", response_model=List[CalendarEventResponse])
def generate_schedule_api(request: ScheduleRequest):
    return generate_schedule_from_request(request)

@router.post("/update", response_model=List[CalendarEventResponse])
def update_schedule_api(request: UpdateRequest):
    return update_schedule_from_request(request)