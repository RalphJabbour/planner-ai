from fastapi import APIRouter, Depends
from typing import List

from .schemas import GenerateRequest, UpdateRequest, CalendarEvent
# from .service import generate_schedule
from .service import update_schedule


router = APIRouter(prefix="/schedule", tags=["scheduler"])

# @router.post("/generate", response_model=List[CalendarEvent])
# async def generate_endpoint(req: GenerateRequest):
#     return generate_schedule(req)


@router.post("/update", response_model=List[CalendarEvent])
async def update_endpoint(req: UpdateRequest):
    return update_schedule(req)
