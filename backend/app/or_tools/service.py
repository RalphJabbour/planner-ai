from sqlalchemy.orm import Session
from app.models.schedule import CalendarEvent, FixedObligation, FlexibleObligation, PersonalizedStudySession
from .optimizer import optimize_schedule
from typing import List, Dict

def generate_schedule(payload: dict, db: Session) -> List[CalendarEvent]:
    # Fetch tasks from the database
    fixed_tasks = db.query(FixedObligation).filter(FixedObligation.student_id == payload["student_id"]).all()
    flexible_tasks = db.query(FlexibleObligation).filter(FlexibleObligation.student_id == payload["student_id"]).all()
    academic_tasks = db.query(PersonalizedStudySession).filter(PersonalizedStudySession.student_id == payload["student_id"]).all()

    # Convert tasks to dictionaries
    fixed_tasks_dict = [task.to_dict() for task in fixed_tasks]
    flexible_tasks_dict = [task.to_dict() for task in flexible_tasks]
    academic_tasks_dict = [task.to_dict() for task in academic_tasks]

    # Call the optimizer
    schedule = optimize_schedule(
        week_start=payload["week_start"],
        fixed_tasks=fixed_tasks_dict,
        flexible_tasks=flexible_tasks_dict,
        academic_tasks=academic_tasks_dict,
    )

    # Save the schedule to the database
    for event in schedule:
        db_event = CalendarEvent(**event)
        db.add(db_event)
    db.commit()

    return schedule

def update_schedule(payload: Dict, db: Session) -> List[CalendarEvent]:
    """
    Update the schedule with new tasks or changes.
    """
    updated_events = []
    for event_data in payload.get("events", []):
        event = db.query(CalendarEvent).filter(CalendarEvent.event_id == event_data["event_id"]).first()
        if event:
            for key, value in event_data.items():
                setattr(event, key, value)
            db.commit()
            db.refresh(event)
            updated_events.append(event)
    return updated_events