from __future__ import annotations
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.schedule import FixedObligation, FlexibleObligation, CalendarEvent
from app.models.academic import AcademicTask
from app.models.course import Course, StudentCourse

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
    Hard-code reasonable defaults so we don't crash.  **REMOVE THIS**
    once the model & migrations add those fields for real!
    ────────────────────────────────────────────────────────────────────
    """
    DEFAULT_SESSION_HOURS = 1        # ← arbitrary 1-hour blocks
    
    # Ensure total hours is a numeric value
    total_raw = d.get("total_hours") or d.get("weekly_target_hours") or 10
    try:
        total = float(total_raw)  # Convert to float to handle Decimal or string values
    except (ValueError, TypeError):
        print(f"Warning: Could not convert {total_raw} to float, using default of 10")
        total = 10.0
    
    # Ensure session hours is a numeric value
    session_raw = d.get("session_hours") or DEFAULT_SESSION_HOURS
    try:
        session = float(session_raw)  # Convert to float to handle Decimal or string values
    except (ValueError, TypeError):
        print(f"Warning: Could not convert {session_raw} to float, using default of 1")
        session = 1.0
    
    # Use obligation_id for consistent identification
    task_id = d.get("id") or d.get("obligation_id")
    print(f"Mapping flexible obligation {task_id} with total_hours={total}, session_hours={session}")
    
    # Make sure we have valid IDs
    if not task_id:
        print("WARNING: No ID found for flexible obligation")
        task_id = f"unknown_{datetime.utcnow().timestamp()}"
        
    # Handle end_date conversion if it's a string
    end_date = d.get("end_date")
    if isinstance(end_date, str):
        try:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except Exception as e:
            print(f"Error converting end_date string to datetime: {e}")
            end_date = None

    return {
        "id": task_id,
        "total_hours": total,
        "session_hours": session,
        "deadline": end_date,        # treat end_date as deadline
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
def update_schedule(payload: dict, db: Session):
    """
    Update the schedule by optimizing tasks
    """
    student_id = payload.get("student_id")
    # If a newly created obligation ID is provided, we'll only delete and recreate events for that obligation
    newly_created_obligation_id = payload.get("newly_created_obligation_id")
    
    if not student_id:
        raise ValueError("Student ID is required")
    
    # Get all fixed and flexible obligations for the student
    fixed_obligations = db.query(FixedObligation).filter(
        FixedObligation.student_id == student_id
    ).all()
    
    flexible_obligations = db.query(FlexibleObligation).filter(
        FlexibleObligation.student_id == student_id
    ).all()
    
    # For academic tasks, join with Course and StudentCourse to get tasks for student's courses
    # Academic tasks are associated with courses, not directly with students
    academic_tasks = db.query(AcademicTask).join(
        Course, AcademicTask.course_id == Course.course_id
    ).join(
        StudentCourse, Course.course_id == StudentCourse.course_id
    ).filter(
        StudentCourse.student_id == student_id,
        AcademicTask.status != "completed"
    ).all()
    
    if not flexible_obligations and not academic_tasks:
        print("No flexible obligations or academic tasks to optimize")
        return []
    
    # Handle selective deletion if a specific obligation ID is provided
    if newly_created_obligation_id:
        # Check if it's a fixed obligation
        is_fixed = any(fo.obligation_id == newly_created_obligation_id for fo in fixed_obligations)
        is_flexible = any(fo.obligation_id == newly_created_obligation_id for fo in flexible_obligations)
        
        if is_fixed:
            print(f"Deleting events for fixed obligation {newly_created_obligation_id}")
            db.query(CalendarEvent).filter(
                CalendarEvent.student_id == student_id,
                CalendarEvent.event_type == "fixed_obligation",
                CalendarEvent.fixed_obligation_id == newly_created_obligation_id
            ).delete()
        elif is_flexible:
            print(f"Deleting events for flexible obligation {newly_created_obligation_id}")
            db.query(CalendarEvent).filter(
                CalendarEvent.student_id == student_id,
                CalendarEvent.event_type == "flexible_obligation",
                CalendarEvent.flexible_obligation_id == newly_created_obligation_id
            ).delete()
        else:
            print(f"Obligation ID {newly_created_obligation_id} not found, not deleting any events")
    else:
        # For a full reschedule, clean all flexible obligation events
        print("Performing full reschedule - deleting all flexible obligation events")
        db.query(CalendarEvent).filter(
            CalendarEvent.student_id == student_id,
            CalendarEvent.event_type == "flexible_obligation"
        ).delete()
    
    # For academic task scheduling, we'll always reschedule all tasks
    db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type == "academic_task"
    ).delete()
    
    # Get existing calendar events to avoid scheduling conflicts
    # For fixed obligations, get all events
    fixed_events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type == "fixed_obligation"
    ).all()
    
    # For flexible obligations, get only events that aren't being rescheduled
    flexible_events = []
    if newly_created_obligation_id:
        flexible_events = db.query(CalendarEvent).filter(
            CalendarEvent.student_id == student_id,
            CalendarEvent.event_type == "flexible_obligation",
            CalendarEvent.flexible_obligation_id != newly_created_obligation_id if is_flexible else True
        ).all()
    
    # Get study sessions and other events that should be preserved
    other_events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type.in_(["study_session", "other"])
    ).all()
    
    existing_events = fixed_events + flexible_events + other_events
    # Map out occupied slots to avoid scheduling conflicts
    occupied_slots = {}
    
    # Create a more detailed structure to track exactly what is occupying each slot
    for event in existing_events:
        start = event.start_time
        end = event.end_time
        
        # Only add events that haven't passed yet
        if end > datetime.now():
            current = start
            while current < end:
                day_key = current.strftime("%Y-%m-%d")
                time_key = current.strftime("%H:%M")
                
                if day_key not in occupied_slots:
                    occupied_slots[day_key] = {}
                
                # Get the correct obligation ID field based on event type
                event_obligation_id = None
                if event.event_type == "fixed_obligation":
                    event_obligation_id = event.fixed_obligation_id
                elif event.event_type == "flexible_obligation":
                    event_obligation_id = event.flexible_obligation_id
                
                occupied_slots[day_key][time_key] = {
                    "event_id": event.event_id,
                    # "title": event.title,
                    "event_type": event.event_type,
                    "obligation_id": event_obligation_id
                }
                
                current += timedelta(minutes=30)
    
    # Create a calendar with the optimizer-compatible format
    calendar = {}
    
    # Determine the date range for optimization
    # Start with today if not specified
    if "week_start" in payload and payload["week_start"]:
        start_date = payload["week_start"]
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Default optimization period is 2 weeks
    optimization_days = 14
    
    # Build the calendar for the optimization period
    for day_offset in range(optimization_days):
        current_date = start_date + timedelta(days=day_offset)
        date_key = current_date.strftime("%Y-%m-%d")
        day_of_week = current_date.strftime("%A").lower()
        
        # Initialize the day in our calendar
        if date_key not in calendar:
            calendar[date_key] = {
                "day_of_week": day_of_week,
                "slots": {}
            }
        
        # Create 30-minute slots for the day (from 6 AM to 10 PM)
        for hour in range(6, 22):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                slot_key = f"{date_key}_{time_str}"
                
                # Check if this slot is already occupied
                is_occupied = False
                conflicting_event = None
                
                if date_key in occupied_slots and time_str in occupied_slots[date_key]:
                    is_occupied = True
                    conflicting_event = occupied_slots[date_key][time_str]
                
                calendar[date_key]["slots"][time_str] = {
                    "occupied": is_occupied,
                    "conflicting_event": conflicting_event
                }
    
    # Create list to hold newly created events
    created_events = []
    
    # Process fixed obligations
    # Fixed obligations are already handled separately, we just make sure to mark their
    # slots as occupied to avoid scheduling conflicts
    
    # Process flexible obligations
    for obligation in flexible_obligations:
        # Skip flexible obligations that aren't being rescheduled, unless doing a full reschedule
        if newly_created_obligation_id and newly_created_obligation_id != obligation.obligation_id and is_flexible:
            print(f"Skipping flexible obligation {obligation.obligation_id} as it's not being rescheduled")
            continue
        
        # Skip obligations that have ended
        if obligation.end_date and obligation.end_date < datetime.now():
            print(f"Skipping flexible obligation {obligation.obligation_id} as it has ended")
            continue
        
        # Skip obligations that haven't started yet
        if obligation.start_date and obligation.start_date > datetime.now() + timedelta(days=optimization_days):
            print(f"Skipping flexible obligation {obligation.obligation_id} as it starts after the optimization period")
            continue
        
        # Calculate total hours to schedule per week
        hours_per_week = obligation.weekly_target_hours or 2  # Default to 2 hours if not specified
        
        # Calculate how many 30-minute slots we need
        slots_needed = hours_per_week * 2
        
        # Make a helper function to actually create an event
        def create_event(obligation, date_str, time_str):
            try:
                start_datetime_str = f"{date_str}T{time_str}:00"
                start_datetime = datetime.fromisoformat(start_datetime_str)
                end_datetime = start_datetime + timedelta(minutes=30)
                
                # Use field 'name' if available, otherwise use 'description' as title
                # This handles different field names in the database model
                if hasattr(obligation, 'name'):
                    title = obligation.name
                else:
                    title = getattr(obligation, 'description', 'Flexible Obligation')
                    
                description = getattr(obligation, 'description', '')
                
                # Create a calendar event with error handling for missing fields
                event = CalendarEvent(
                    student_id=student_id,
                    # title=title,
                    # description=description,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    event_type="flexible_obligation",
                    flexible_obligation_id=obligation.obligation_id,
                    location=getattr(obligation, 'location', None),
                    # Add missing required fields with defaults
                    date=start_datetime.date(),
                    status="scheduled"
                )
                
                db.add(event)
                db.flush()  # Get the event ID without committing
                created_events.append(event)
                return event
            except Exception as e:
                print(f"Error creating flexible obligation event: {e}")
                import traceback
                print(traceback.format_exc())
                return None
        
        # Calculate how many slots we've scheduled so far
        slots_scheduled = 0
        
        # Get the constraint days, or default to all days
        constraint_days = []
        if obligation.constraints:
            for constraint in obligation.constraints:
                if constraint.get("type") == "day_of_week":
                    day = constraint.get("value", "").lower()
                    if day:
                        constraint_days.append(day)
        
        # If no constraint days are specified, use all days
        if not constraint_days:
            constraint_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        # Distribute events evenly across days, respecting constraints
        date_keys = sorted(calendar.keys())
        for date_key in date_keys:
            day_of_week = calendar[date_key]["day_of_week"]
            
            # Skip days that don't match the constraints
            if day_of_week not in constraint_days:
                continue
            
            # Skip dates outside the obligation's date range
            date_obj = datetime.strptime(date_key, "%Y-%m-%d")
            if obligation.start_date and obligation.start_date > date_obj:
                continue
            if obligation.end_date and obligation.end_date < date_obj:
                continue
            
            # Schedule up to 2 slots per day (1 hour), unless we need to catch up
            slots_per_day = min(2, slots_needed - slots_scheduled)
            day_slots_scheduled = 0
            
            # Iterate through time slots
            time_slots = sorted(calendar[date_key]["slots"].keys())
            for time_str in time_slots:
                slot = calendar[date_key]["slots"][time_str]
                
                # Skip occupied slots
                if slot["occupied"]:
                    # Debug: print what's occupying the slot if needed
                    # if slot.get("conflicting_event"):
                    #     print(f"Slot {date_key} {time_str} occupied by: {slot['conflicting_event']}")
                    continue
                
                # Create an event for this slot
                event = create_event(obligation, date_key, time_str)
                if event:
                    # Mark the slot as occupied
                    calendar[date_key]["slots"][time_str]["occupied"] = True
                    calendar[date_key]["slots"][time_str]["conflicting_event"] = {
                        "event_id": event.event_id,
                        "title": event.title,
                        "event_type": "flexible_obligation",
                        "obligation_id": event.flexible_obligation_id
                    }
                    
                    # Update counters
                    slots_scheduled += 1
                    day_slots_scheduled += 1
                    
                    # Break if we've scheduled enough slots for this day
                    if day_slots_scheduled >= slots_per_day:
                        break
            
            # Break if we've scheduled all the slots we need
            if slots_scheduled >= slots_needed:
                break
    
    # Process academic tasks (similar to flexible obligations)
    for task in academic_tasks:
        # Skip tasks that are already completed
        if task.status == "completed":
            continue
        
        # Skip tasks with no due date or that are already late
        if not task.due_date or task.due_date < datetime.now():
            continue
        
        # Calculate estimated time needed and convert to 30-min slots
        estimated_minutes = task.estimated_time_minutes or 60  # Default 1 hour if not specified
        slots_needed = max(1, round(estimated_minutes / 30))  # At least 1 slot
        
        # Make a helper function to create an event
        def create_task_event(task, date_str, time_str):
            try:
                start_datetime_str = f"{date_str}T{time_str}:00"
                start_datetime = datetime.fromisoformat(start_datetime_str)
                end_datetime = start_datetime + timedelta(minutes=30)
                
                # Get title with fallback
                task_title = getattr(task, 'title', None) or getattr(task, 'name', 'Academic Task')
                
                # Create a calendar event
                event = CalendarEvent(
                    student_id=student_id,
                    title=f"Work on: {task_title}",
                    description=getattr(task, 'description', ''),
                    start_time=start_datetime,
                    end_time=end_datetime,
                    event_type="academic_task",
                    task_id=task.task_id,
                    date=start_datetime.date(),
                    status="scheduled"
                )
                
                db.add(event)
                db.flush()  # Get the event ID without committing
                created_events.append(event)
                return event
            except Exception as e:
                print(f"Error creating academic task event: {e}")
                import traceback
                print(traceback.format_exc())
                return None
        
        # Calculate deadline for scheduling (we want to schedule all tasks at least 1 day before due date)
        deadline = task.due_date - timedelta(days=1)
        deadline_str = deadline.strftime("%Y-%m-%d")
        
        # Prioritize scheduling based on due date - find valid dates up to deadline
        valid_dates = []
        date_keys = sorted(calendar.keys())
        for date_key in date_keys:
            date_obj = datetime.strptime(date_key, "%Y-%m-%d")
            if date_obj <= deadline:
                valid_dates.append(date_key)
        
        # If no valid dates, skip this task
        if not valid_dates:
            print(f"No valid dates before deadline for task {task.task_id}")
            continue
        
        # Calculate slots scheduled so far
        slots_scheduled = 0
        
        # Try to distribute task events across days approaching the deadline
        for date_key in valid_dates:
            # Schedule up to 4 slots per day (2 hours max per day)
            slots_per_day = min(4, slots_needed - slots_scheduled)
            day_slots_scheduled = 0
            
            # Iterate through time slots
            time_slots = sorted(calendar[date_key]["slots"].keys())
            for time_str in time_slots:
                slot = calendar[date_key]["slots"][time_str]
                
                # Skip occupied slots
                if slot["occupied"]:
                    continue
                
                # Create an event for this slot
                event = create_task_event(task, date_key, time_str)
                if event:
                    # Mark the slot as occupied
                    calendar[date_key]["slots"][time_str]["occupied"] = True
                    calendar[date_key]["slots"][time_str]["conflicting_event"] = {
                        "event_id": event.event_id,
                        "title": event.title,
                        "event_type": "academic_task",
                        "task_id": event.task_id
                    }
                    
                    # Update counters
                    slots_scheduled += 1
                    day_slots_scheduled += 1
                    
                    # Break if we've scheduled enough slots for this day
                    if day_slots_scheduled >= slots_per_day:
                        break
            
            # Break if we've scheduled all the slots we need
            if slots_scheduled >= slots_needed:
                break
    
    # Commit all events to the database
    db.commit()
    
    # Refresh events to get their IDs
    for event in created_events:
        db.refresh(event)
    
    # Return the created events
    return [
        {
            "event_id": event.event_id,
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "event_type": event.event_type,
            "obligation_id": getattr(event, "fixed_obligation_id", None) or getattr(event, "flexible_obligation_id", None),
            "task_id": getattr(event, "task_id", None)
        }
        for event in created_events
    ]
