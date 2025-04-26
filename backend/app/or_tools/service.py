from __future__ import annotations
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.schedule import FixedObligation, FlexibleObligation, CalendarEvent
from app.models.academic import AcademicTask
from app.models.course import Course, StudentCourse

from .optimizer import update_schedule as optimize_schedule

from sqlalchemy.exc import SQLAlchemyError


# ──────────────────────────────────────────────────────────────────────────
# Mapping helpers – convert ORM objects to optimizer dict format
# ──────────────────────────────────────────────────────────────────────────

def _map_fixed_obligation(obligation, week_start: datetime) -> Dict:
    """Convert a FixedObligation to the format expected by the optimizer"""
    # Create a datetime for this day's occurrence of the obligation
    days_map = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    
    # Create events for this fixed obligation
    events = []
    
    # Handle each day of the week this obligation occurs on
    if not hasattr(obligation, 'days_of_week') or not obligation.days_of_week:
        return None
        
    for day_name in obligation.days_of_week:
        # Get weekday index (0-6)
        day_idx = days_map.get(day_name)
        if day_idx is None:
            continue
            
        # Calculate the date for this weekday
        days_until = (day_idx - week_start.weekday()) % 7
        event_date = week_start + timedelta(days=days_until)
        
        # Skip if event_date is outside the obligation's date range
        if obligation.start_date and event_date.date() < obligation.start_date.date():
            continue
        if obligation.end_date and event_date.date() > obligation.end_date.date():
            continue
            
        # Create start and end times for this event
        start_time = datetime.combine(event_date.date(), obligation.start_time)
        end_time = datetime.combine(event_date.date(), obligation.end_time)
        
        # Add to events list
        return {
            "id": f"fixed_{obligation.obligation_id}_{day_name}",
            "start": start_time,
            "end": end_time,
            "priority": getattr(obligation, 'priority', 10),  # Fixed obligations have highest priority
            "obligation_id": obligation.obligation_id
        }
    
    return None


def _map_flexible_obligation(obligation) -> Dict:
    """Convert a FlexibleObligation to the format expected by the optimizer"""
    # Ensure total hours is a numeric value
    try:
        total_hours = float(obligation.weekly_target_hours) if obligation.weekly_target_hours else 2.0
    except (ValueError, TypeError):
        total_hours = 2.0
        
    # Default to 1-hour sessions
    session_hours = 1.0
    
    # Handle constraints
    constraints = []
    if obligation.constraints:
        if isinstance(obligation.constraints, list):
            constraints = obligation.constraints
        elif isinstance(obligation.constraints, dict):
            # Convert dict to list if needed
            constraints = [obligation.constraints]
            
    return {
        "id": f"flex_{obligation.obligation_id}",
        "total_hours": total_hours,
        "session_hours": session_hours,
        "deadline": obligation.end_date,
        "priority": getattr(obligation, 'priority', 5),
        "dependencies": [],
        "obligation_id": obligation.obligation_id
    }


def _map_academic_task(task) -> Dict:
    """Convert an AcademicTask to the format expected by the optimizer"""
    # Default to 1 hour if not specified
    try:
        estimated_minutes = float(task.estimated_time_minutes) if hasattr(task, 'estimated_time_minutes') and task.estimated_time_minutes else 60.0
    except (ValueError, TypeError):
        estimated_minutes = 60.0
        
    # Convert minutes to hours
    total_hours = estimated_minutes / 60.0
    
    # Default to 1-hour sessions
    session_hours = min(1.0, total_hours)
    
    return {
        "id": f"academic_{task.task_id}",
        "total_hours": total_hours,
        "session_hours": session_hours,
        "deadline": task.due_date,
        "priority": getattr(task, 'priority', 8),
        "dependencies": [],
        "task_id": task.task_id
    }


def _to_datetime(week_start: datetime, t: str | time) -> datetime:
    """Attach a time-of-day to the week_start date."""
    if isinstance(t, str):
        t = datetime.strptime(t, "%H:%M:%S").time()
    return datetime.combine(week_start.date(), t)


# ──────────────────────────────────────────────────────────────────────────
# Main update function
# ──────────────────────────────────────────────────────────────────────────
def update_schedule(payload: dict, db: Session):
    """
    Update the schedule by optimizing tasks.
    
    This function:
    1. Fetches all obligations and tasks
    2. Treats fixed obligations as immovable time slots
    3. Considers all flexible obligations (existing and new) for optimization
    4. Passes everything to the optimizer
    5. Replaces all flexible events with newly optimized schedule
    
    Returns a list of created events.
    """
    # Get student ID from payload
    student_id = payload.get("student_id")
    if not student_id:
        raise ValueError("Student ID is required")
    
    print(f"Updating schedule for student {student_id}")
    
    # Determine start date for optimization
    if "week_start" in payload and payload["week_start"]:
        week_start = payload["week_start"]
        if isinstance(week_start, str):
            week_start = datetime.fromisoformat(week_start)
    else:
        # Start from beginning of current day
        week_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"Week start: {week_start}")
    
    # Fetch all obligations and tasks
    fixed_obligations = db.query(FixedObligation).filter(
        FixedObligation.student_id == student_id
    ).all()
    
    flexible_obligations = db.query(FlexibleObligation).filter(
        FlexibleObligation.student_id == student_id
    ).all()
    
    # For academic tasks, join with Course and StudentCourse to get tasks for student's courses
    academic_tasks = db.query(AcademicTask).join(
        Course, AcademicTask.course_id == Course.course_id
    ).join(
        StudentCourse, Course.course_id == StudentCourse.course_id
    ).filter(
        StudentCourse.student_id == student_id,
        AcademicTask.status != "completed"
    ).all()
    
    # Get existing fixed calendar events - these will be preserved as fixed slots
    fixed_events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type == "fixed_obligation"
    ).all()
    
    # Get other events that should be preserved (not flexible or academic)
    other_events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.event_type.in_(["other"])
    ).all()
    
    print(f"Found {len(fixed_events)} fixed events and {len(other_events)} other events to preserve")
    print(f"Found {len(flexible_obligations)} flexible obligations and {len(academic_tasks)} academic tasks to optimize")
    
    # Convert to optimizer format
    fixed_tasks = []
    
    # Add fixed obligation events as immovable slots
    for event in fixed_events:
        # Skip events that have already passed
        if event.end_time < datetime.now():
            continue
            
        fixed_tasks.append({
            "id": f"fixed_{event.event_id}",
            "start": event.start_time,
            "end": event.end_time,
            "priority": 10,  # Highest priority
        })
    
    # Add other events as immovable slots
    for event in other_events:
        # Skip events that have already passed
        if event.end_time < datetime.now():
            continue
            
        fixed_tasks.append({
            "id": f"other_{event.event_id}",
            "start": event.start_time,
            "end": event.end_time,
            "priority": 5,  # Medium priority
        })
    
    # Add all flexible obligations to be scheduled
    flexible_tasks = []
    for obligation in flexible_obligations:
        # Skip obligations that have ended
        if obligation.end_date and obligation.end_date < datetime.now():
            continue
            
        flexible_tasks.append(_map_flexible_obligation(obligation))
    
    # Add all academic tasks
    academic_task_list = []
    for task in academic_tasks:
        # Skip tasks with no due date or that are already late
        if not task.due_date or task.due_date < datetime.now():
            continue
            
        academic_task_list.append(_map_academic_task(task))
    
    print(f"Passing to optimizer: {len(fixed_tasks)} fixed tasks, {len(flexible_tasks)} flexible tasks, {len(academic_task_list)} academic tasks")
    
    # If no tasks to optimize, return empty list
    if not (flexible_tasks or academic_task_list):
        print("No flexible obligations or academic tasks to optimize")
        return []
    
    # Delete all existing flexible and academic task events before creating new ones
    # This ensures we don't have duplicates
    try:
        deleted_count = db.query(CalendarEvent).filter(
            CalendarEvent.student_id == student_id,
            CalendarEvent.event_type.in_(["flexible_obligation", "academic_task", "study_session"])
        ).delete()
        print(f"Deleted {deleted_count} existing flexible/academic events")
    except Exception as e:
        print(f"Error deleting existing events: {e}")
        import traceback
        print(traceback.format_exc())
        # Continue anyway to ensure we create new events
    
    # Call the optimizer
    try:
        optimize_schedule(
            student_id=student_id,
        )
        
        # Add commit here
        db.commit()
        print("Changes committed to database")
        
        # Return success message or empty list
        return []
    except Exception as e:
        print(f"Error in optimizer: {e}")
        import traceback
        print(traceback.format_exc())
        db.rollback()  # Make sure to rollback on error
        return []
