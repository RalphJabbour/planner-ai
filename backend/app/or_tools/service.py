from __future__ import annotations
import logging
from datetime import datetime, time
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.schedule import CalendarEvent, FixedObligation, FlexibleObligation, PersonalizedStudySession
from .optimizer import optimize_schedule

from sqlalchemy.exc import SQLAlchemyError


# ──────────────────────────────────────────────────────────────────────────
# Mapping helpers – convert ORM dict → optimizer dict
# ──────────────────────────────────────────────────────────────────────────

def _map_fixed(d: Dict, week_start: datetime) -> Dict:
    return {
        "id": d.get("id") or d.get("obligation_id"),
        "start": _to_datetime(week_start, d["start_time"]),
        "end":   _to_datetime(week_start, d["end_time"]),
        "priority": d.get("priority", 1),
    }



def _map_flexible(d: Dict) -> Dict:
    """
    FlexibleObligation rows coming from the DB **do NOT** yet contain
    the columns the optimiser expects (`total_hours`, `session_hours`).

    ─── TEMPORARY HOT-FIX ──────────────────────────────────────────────
    Hard-code reasonable defaults so we don’t crash.  **REMOVE THIS**
    once the model & migrations add those fields for real!
    ────────────────────────────────────────────────────────────────────
    """
    DEFAULT_SESSION_HOURS = 1        # ← arbitrary 1-hour blocks
    total = (
        d.get("total_hours")          # real column (missing today)
        or d.get("weekly_target_hours")  # close enough
        or 10                          # fallback to avoid KeyError
    )
    session = d.get("session_hours") or DEFAULT_SESSION_HOURS

    return {
        "id": d.get("id") or d.get("obligation_id"),
        "total_hours": total,
        "session_hours": session,
        "deadline": d.get("end_date"),        # treat end_date as deadline
        "priority": d.get("priority", 5),
        "dependencies": d.get("dependencies", []),
        "max_per_day": d.get("max_per_day"),
    }


def _map_academic(d: Dict) -> Dict:
    return {
        "id": d.get("id") or d.get("task_id"),
        "total_hours": d["total_hours"],
        "session_hours": d["session_hours"],
        "deadline": d["deadline"],
        "priority": d.get("priority", 8),
        "dependencies": d.get("dependencies", []),
    }
    
def _to_datetime(week_start: datetime, t: str | time) -> datetime:
    """Attach a time-of-day to the week_start date."""
    if isinstance(t, str):
        t = datetime.strptime(t, "%H:%M:%S").time()
    return datetime.combine(week_start.date(), t)


# ──────────────────────────────────────────────────────────────────────────
# Main update function (prints preserved)
# ──────────────────────────────────────────────────────────────────────────
def update_schedule(payload: Dict, db: Session) -> List[CalendarEvent]:
    print("Entered the update_schedule function xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

    student_id = payload.get("student_id")
    if not student_id:
        raise ValueError("Student ID is required to update the schedule")

    # fetch tasks
    fixed_tasks = db.query(FixedObligation).filter(FixedObligation.student_id == student_id).all()
    flexible_tasks = db.query(FlexibleObligation).filter(FlexibleObligation.student_id == student_id).all()
    academic_tasks = db.query(PersonalizedStudySession).filter(PersonalizedStudySession.student_id == student_id).all()

    # reference week_start (today if not supplied)
    week_start = payload.get("week_start", datetime.utcnow())

    # ORM → dict → optimizer dicts
    fixed_dicts = [_map_fixed(t.to_dict(), week_start) for t in fixed_tasks]
    flex_dicts  = [_map_flexible(t.to_dict())          for t in flexible_tasks]
    acad_dicts  = [_map_academic(t.to_dict())          for t in academic_tasks]

    # Debug prints you had
    print("Fixed Tasks: ", fixed_dicts)
    print("Flexible Tasks: ", flex_dicts)
    print("Academic Tasks: ", acad_dicts)
    print("heeree i ammmmmmmm")

    # call optimizer
    try:
        schedule = optimize_schedule(
            week_start=week_start,
            fixed_tasks=fixed_dicts,
            flexible_tasks=flex_dicts,
            academic_tasks=acad_dicts,
        )
    except ValueError as e:
        logging.error("Invalid task data: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Unexpected optimizer crash")
        raise HTTPException(status_code=500, detail="Error updating schedule")

    print("Optimized Schedule: ", schedule)
    if not schedule:
        print("No schedule generated. Please check your tasks and try again.")
        return []

    # Replace existing CalendarEvents for this student
    # delete old events for the student
    # db.query(CalendarEvent).filter(CalendarEvent.student_id == student_id).delete()
    # AFTER  – keep fixed_obligation rows intact
    db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type != "fixed_obligation"
    ).delete()

    for ev in schedule:
        db_event = CalendarEvent(
            student_id=student_id,
            event_type=ev["type"],
            fixed_obligation_id=ev["id"] if ev["type"] == "fixed_obligation" else None,
            flexible_obligation_id=None,
            study_session_id=None,
            date=ev["start_time"],        # TIMESTAMP column accepts full datetime
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            priority=1,
            status="scheduled",
        )
        print("→ adding CalendarEvent:", db_event.event_type, db_event.start_time)
        db.add(db_event)

    try:
        db.flush()            # forces INSERTs; any FK / NOT-NULL errors appear now
    except SQLAlchemyError as e:
        db.rollback()
        logging.exception("DB error while inserting calendar events")
        raise HTTPException(status_code=500, detail="CalendarEvent insert failed") from e

    db.commit()
    print("committed calendar events")
    return schedule
