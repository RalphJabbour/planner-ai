from .optimizer import optimize_schedule, update_schedule_with_new_tasks
from .schemas import ScheduleRequest, UpdateRequest

def generate_schedule_from_request(request: ScheduleRequest):
    return optimize_schedule(request.dict())

def update_schedule_from_request(request: UpdateRequest):
    return update_schedule_with_new_tasks(
        old_events=[event.dict() for event in request.old_events],
        new_tasks=request.new_tasks.dict()
    )