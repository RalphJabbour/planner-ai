from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import time
from app.database import get_db
from app.models.student import Student
from app.models.schedule import FixedObligation, FlexibleObligation, CalendarEvent
from app.auth.token import get_current_student
from datetime import datetime, timedelta
from app.models.academic import AcademicTask
from app.models.course import Course, StudentCourse
import logging

router = APIRouter(prefix="/tasks", tags=["tasks"])

# ---- Fixed Obligations ----

class FixedObligationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: time
    end_time: time
    days_of_week: List[str]  # Changed from day_of_week to days_of_week List
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    recurrence: Optional[str] = None  # e.g., "weekly", "biweekly"
    priority: Optional[int] = 3  # Default priority of 3 (medium)

class FixedObligationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    days_of_week: Optional[List[str]] = None  # Changed from day_of_week to days_of_week List
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    recurrence: Optional[str] = None
    priority: Optional[int] = None

# ---- Calendar Events ----

class CalendarEventCreate(BaseModel):
    event_type: str  # 'fixed_obligation', 'flexible_obligation', 'study_session', or 'class'
    fixed_obligation_id: Optional[int] = None
    flexible_obligation_id: Optional[int] = None
    study_session_id: Optional[int] = None
    date: datetime
    start_time: datetime
    end_time: datetime
    priority: Optional[int] = 3
    status: Optional[str] = "scheduled"

class CalendarEventUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    priority: Optional[int] = None
    status: Optional[str] = None

@router.get("/fixed", operation_id="get_fixed_obligations")
async def get_fixed_obligations(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get all fixed obligations for the current student"""
    obligations = db.query(FixedObligation).filter(
        FixedObligation.student_id == current_student.student_id
    ).all()
    
    return obligations

# Update your create_fixed_obligation function to handle days_of_week JSON array
@router.post("/fixed", operation_id="create_fixed_obligation")
async def create_fixed_obligation(
    obligation: FixedObligationCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Create a new fixed obligation for the current student
        + add events to calendar
    """

    # Validate priority
    if obligation.priority and (obligation.priority < 1 or obligation.priority > 5):
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 5")
    
    # Validate days_of_week entries
    valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in obligation.days_of_week:
        if day not in valid_days:
            raise HTTPException(status_code=400, detail=f"Invalid day of week: {day}. Must be one of {valid_days}")
    
    # Create the obligation object
    new_obligation = FixedObligation(
        student_id=current_student.student_id,
        name=obligation.name,
        description=obligation.description,
        start_time=obligation.start_time,
        end_time=obligation.end_time,
        days_of_week=obligation.days_of_week,  # Now using days_of_week array
        start_date=obligation.start_date,
        end_date=obligation.end_date,
        recurrence=obligation.recurrence,
        priority=obligation.priority
    )
    
    db.add(new_obligation)
    db.commit()
    db.refresh(new_obligation)

    # Create calendar events corresponding to the fixed obligation
    try:
        today = datetime.now()
        days_of_week = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        # Create events for each day in days_of_week
        for day_name in obligation.days_of_week:
            # Calculate the next occurrence of this day of the week
            target_day = days_of_week.get(day_name)
            if target_day is None:
                logging.warning(f"Invalid day of week: {day_name}")
                continue
                
            current_day = today.weekday()
            days_until_target = (target_day - current_day) % 7
            
            # If it's the same day but time has passed, start from next week
            if days_until_target == 0 and obligation.start_time < today.time():
                days_until_target = 7
            
            next_occurrence = today + timedelta(days=days_until_target)
            next_occurrence = next_occurrence.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if this occurrence is within the start_date and end_date constraints
            if obligation.start_date and next_occurrence.date() < obligation.start_date.date():
                next_occurrence = obligation.start_date
            
            if obligation.recurrence == "monthly":
                for i in range(1, 7): # 6 months ahead
                    event_date = next_occurrence + timedelta(days=i*30)
                    if obligation.end_date and event_date.date() > obligation.end_date.date():
                        continue
                    start_datetime = datetime.combine(event_date.date(), obligation.start_time)
                    end_datetime = datetime.combine(event_date.date(), obligation.end_time)
                    calendar_event = CalendarEvent(
                        student_id=current_student.student_id,
                        event_type="fixed_obligation",
                        fixed_obligation_id=new_obligation.obligation_id,
                        date=event_date,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        priority=obligation.priority,
                        status="scheduled"
                    )
                    db.add(calendar_event)
            else:
                # Number of weeks to generate events for
                weeks_ahead = 26 #52

                # Create events for each occurrence
                for i in range(0, weeks_ahead, 1 if obligation.recurrence != "biweekly" else 2):
                    event_date = next_occurrence + timedelta(days=i*7)
                    
                    # Skip if beyond end_date
                    if obligation.end_date and event_date.date() > obligation.end_date.date():
                        continue
                    # Convert time objects to datetime for the specific date
                    start_datetime = datetime.combine(event_date.date(), obligation.start_time)
                    end_datetime = datetime.combine(event_date.date(), obligation.end_time)
                    
                    calendar_event = CalendarEvent(
                        student_id=current_student.student_id,
                        event_type="fixed_obligation",
                        fixed_obligation_id=new_obligation.obligation_id,
                        date=event_date,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        priority=obligation.priority,
                        status="scheduled"
                    )
                    
                    db.add(calendar_event)
        
        logging.info(f"Created calendar events for fixed obligation ID: {new_obligation.obligation_id}")    
        db.commit()
    except Exception as e:
        logging.error(f"Failed to create calendar events: {str(e)}")
        # The obligation was already created successfully, so we don't want to fail the whole request
    
    return new_obligation

@router.get("/fixed/{obligation_id}", operation_id="get_fixed_obligation")
async def get_fixed_obligation(
    obligation_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get a specific fixed obligation by ID"""
    db_obligation = db.query(FixedObligation).filter(
        FixedObligation.obligation_id == obligation_id,
        FixedObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Fixed obligation not found or not owned by this student")
    
    return db_obligation

@router.put("/fixed/{obligation_id}", operation_id="update_fixed_obligation")
async def update_fixed_obligation(
    obligation_id: int,
    obligation_update: FixedObligationUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Update an existing fixed obligation
        + edit events in calendar
    """
    # Check if obligation exists and belongs to the student
    db_obligation = db.query(FixedObligation).filter(
        FixedObligation.obligation_id == obligation_id,
        FixedObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Fixed obligation not found or not owned by this student")
    
    # Validate priority if provided
    if obligation_update.priority and (obligation_update.priority < 1 or obligation_update.priority > 5):
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 5")
    
    # Check if we're updating schedule-related fields
    schedule_updated = any(field in obligation_update.dict(exclude_unset=True) 
                          for field in ['days_of_week', 'start_time', 'end_time', 'recurrence', 'start_date', 'end_date'])
    
    # Update fields that are provided
    update_data = obligation_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obligation, key, value)
    
    db.commit()
    db.refresh(db_obligation)
    
    # If schedule-related fields were updated, regenerate the calendar events
    if schedule_updated:
        try:
            # Delete all future calendar events for this obligation
            future_events = db.query(CalendarEvent).filter(
                CalendarEvent.fixed_obligation_id == obligation_id,
                CalendarEvent.start_time >= datetime.now()
            ).all()
            
            for event in future_events:
                db.delete(event)
            db.commit()
            
            # Create new calendar events with the updated schedule
            today = datetime.now()
            days_of_week = {
                "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
                "Friday": 4, "Saturday": 5, "Sunday": 6
            }
            
            # For each day in days_of_week
            for day_name in db_obligation.days_of_week:
                # Calculate the next occurrence of this day of the week
                target_day = days_of_week.get(day_name)
                if target_day is None:
                    logging.warning(f"Invalid day of week: {day_name}")
                    continue
                    
                current_day = today.weekday()
                days_until_target = (target_day - current_day) % 7
                
                # If it's the same day but time has passed, start from next week
                if days_until_target == 0 and db_obligation.start_time < today.time():
                    days_until_target = 7
                
                next_occurrence = today + timedelta(days=days_until_target)
                next_occurrence = next_occurrence.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Check if this occurrence is within the start_date constraint
                if db_obligation.start_date and next_occurrence.date() < db_obligation.start_date.date():
                    next_occurrence = db_obligation.start_date
                
                if db_obligation.recurrence == "monthly":
                    for i in range(1, 7): # 6 months ahead
                        event_date = next_occurrence + timedelta(days=i*30)
                        if db_obligation.end_date and event_date.date() > db_obligation.end_date.date():
                            continue
                        start_datetime = datetime.combine(event_date.date(), db_obligation.start_time)
                        end_datetime = datetime.combine(event_date.date(), db_obligation.end_time)
                        calendar_event = CalendarEvent(
                            student_id=current_student.student_id,
                            event_type="fixed_obligation",
                            fixed_obligation_id=db_obligation.obligation_id,
                            date=event_date,
                            start_time=start_datetime,
                            end_time=end_datetime,
                            priority=db_obligation.priority,
                            status="scheduled"
                        )
                        db.add(calendar_event)
                else:
                    # Number of weeks to generate events for
                    weeks_ahead = 26 #52
                    # Create events for each occurrence
                    for i in range(0, weeks_ahead, 1 if db_obligation.recurrence != "biweekly" else 2):
                        event_date = next_occurrence + timedelta(days=i*7)
                        
                        # Skip if beyond end_date
                        if db_obligation.end_date and event_date.date() > db_obligation.end_date.date():
                            continue
                        
                        # Convert time objects to datetime for the specific date
                        start_datetime = datetime.combine(event_date.date(), db_obligation.start_time)
                        end_datetime = datetime.combine(event_date.date(), db_obligation.end_time)
                        
                        calendar_event = CalendarEvent(
                            student_id=current_student.student_id,
                            event_type="fixed_obligation",
                            fixed_obligation_id=db_obligation.obligation_id,
                            date=event_date,
                            start_time=start_datetime,
                            end_time=end_datetime,
                            priority=db_obligation.priority,
                            status="scheduled"
                        )
                        
                        db.add(calendar_event)
            logging.info(f"Updated calendar events for fixed obligation ID: {db_obligation.obligation_id}")
            db.commit()
        except Exception as e:
            logging.error(f"Failed to update calendar events: {str(e)}")
            # The obligation was already updated successfully, so we don't want to fail the whole request
    
    return db_obligation

@router.delete("/fixed/{obligation_id}", operation_id="delete_fixed_obligation")
async def delete_fixed_obligation(
    obligation_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Delete a fixed obligation"""
    # Check if obligation exists and belongs to the student
    db_obligation = db.query(FixedObligation).filter(
        FixedObligation.obligation_id == obligation_id,
        FixedObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Fixed obligation not found or not owned by this student")
    
    # Delete associated calendar events
    try:
        from app.models.schedule import CalendarEvent
        
        # Find and delete all calendar events associated with this obligation
        calendar_events = db.query(CalendarEvent).filter(
            CalendarEvent.fixed_obligation_id == obligation_id
        ).all()
        
        for event in calendar_events:
            db.delete(event)
    except Exception as e:
        logging.error(f"Failed to delete associated calendar events: {str(e)}")
    
    # Delete the obligation itself
    db.delete(db_obligation)
    db.commit()
    
    return {"message": "Fixed obligation deleted successfully"}

# ---- Flexible Obligations ----

class FlexibleObligationCreate(BaseModel):
    description: str
    weekly_target_hours: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: Optional[int] = 3  # Default priority of 3 (medium)
    constraints: Optional[Dict[str, Any]] = None

class FlexibleObligationUpdate(BaseModel):
    description: Optional[str] = None
    weekly_target_hours: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: Optional[int] = None
    constraints: Optional[Dict[str, Any]] = None

@router.get("/flexible", operation_id="get_flexible_obligations")
async def get_flexible_obligations(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get all flexible obligations for the current student"""
    obligations = db.query(FlexibleObligation).filter(
        FlexibleObligation.student_id == current_student.student_id
    ).all()
    
    return obligations

@router.get("/flexible/{obligation_id}", operation_id="get_flexible_obligation")
async def get_flexible_obligation(
    obligation_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get a specific flexible obligation by ID"""
    db_obligation = db.query(FlexibleObligation).filter(
        FlexibleObligation.obligation_id == obligation_id,
        FlexibleObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Flexible obligation not found or not owned by this student")
    
    return db_obligation

@router.post("/flexible", operation_id="create_flexible_obligation")
async def create_flexible_obligation(
    obligation: FlexibleObligationCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Create a new flexible obligation for the current student"""
    # Validate priority if provided
    if obligation.priority and (obligation.priority < 1 or obligation.priority > 5):
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 5")
    
    new_obligation = FlexibleObligation(
        student_id=current_student.student_id,
        description=obligation.description,
        weekly_target_hours=obligation.weekly_target_hours,
        start_date=obligation.start_date,
        end_date=obligation.end_date,
        priority=obligation.priority,
        constraints=obligation.constraints
    )
    
    db.add(new_obligation)
    db.commit()
    db.refresh(new_obligation)
    
    return new_obligation

@router.put("/flexible/{obligation_id}", operation_id="update_flexible_obligation")
async def update_flexible_obligation(
    obligation_id: int,
    obligation_update: FlexibleObligationUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Update an existing flexible obligation"""
    # Check if obligation exists and belongs to the student
    db_obligation = db.query(FlexibleObligation).filter(
        FlexibleObligation.obligation_id == obligation_id,
        FlexibleObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Flexible obligation not found or not owned by this student")
    
    # Validate priority if provided
    if obligation_update.priority and (obligation_update.priority < 1 or obligation_update.priority > 5):
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 5")
    
    # Update fields that are provided
    update_data = obligation_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obligation, key, value)
    
    db.commit()
    db.refresh(db_obligation)
    
    return db_obligation

@router.delete("/flexible/{obligation_id}", operation_id="delete_flexible_obligation")
async def delete_flexible_obligation(
    obligation_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Delete a flexible obligation"""
    # Check if obligation exists and belongs to the student
    db_obligation = db.query(FlexibleObligation).filter(
        FlexibleObligation.obligation_id == obligation_id,
        FlexibleObligation.student_id == current_student.student_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Flexible obligation not found or not owned by this student")
    
    db.delete(db_obligation)
    db.commit()
    
    return {"message": "Flexible obligation deleted successfully"}

# ---- Academic Tasks ----

@router.get("/academic-tasks", operation_id="get_academic_tasks")
async def get_academic_tasks(
    days: int = 7,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get upcoming academic tasks for the current student within a specified number of days"""
    # First, fetch the courses registered by the student
    registered_courses = db.query(Course).\
        join(StudentCourse, StudentCourse.course_id == Course.course_id).\
        filter(StudentCourse.student_id == current_student.student_id).\
        all()
    
    # Get the course IDs
    course_ids = [course.course_id for course in registered_courses]
    
    # If the student has no registered courses, return empty list
    if not course_ids:
        return []
    
    # Calculate the date range
    now = datetime.now()
    end_date = now + timedelta(days=days)
    
    # Query tasks for the student's registered courses that are due within the date range
    tasks = db.query(AcademicTask).filter(
        AcademicTask.course_id.in_(course_ids),
        AcademicTask.deadline >= now,
        AcademicTask.deadline <= end_date
    ).order_by(AcademicTask.deadline).all()
    
    return tasks

@router.get("/academic-tasks/course/{course_id}", operation_id="get_academic_tasks_by_course")
async def get_academic_tasks_by_course(
    course_id: int,
    days: Optional[int] = None,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get all academic tasks for a specific course that belong to the current student.
    Optionally filter by tasks due within a specified number of days."""
    
    # First check if the student is registered for this course
    is_registered = db.query(StudentCourse).filter(
        StudentCourse.student_id == current_student.student_id,
        StudentCourse.course_id == course_id
    ).first()
    
    if not is_registered:
        raise HTTPException(status_code=403, detail="Student is not registered for this course")
    
    query = db.query(AcademicTask).filter(
        AcademicTask.course_id == course_id
    )
    
    if days is not None:
        now = datetime.now()
        end_date = now + timedelta(days=days)
        query = query.filter(
            AcademicTask.deadline >= now,
            AcademicTask.deadline <= end_date
        )
    
    tasks = query.order_by(AcademicTask.deadline).all()
    
    if not tasks:
        return []
    
    return tasks

class AcademicTaskCreate(BaseModel):
    course_id: int
    task_name: str
    description: Optional[str] = None
    deadline: datetime
    priority: Optional[int] = 3  # Default priority of 3 (medium)

#needs a special api key to only be accessed by the IEP that
# generate the academic
@router.post("/academic-tasks")
async def create_academic_task(
    task: AcademicTaskCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    # """Create a new academic task for the current student"""
    # # Check if the course exists and belongs to the student
    # course = db.query(Course).filter(
    #     Course.course_id == task.course_id,
    #     Course.student_id == current_student.student_id
    # ).first()
    
    # if not course:
    #     raise HTTPException(status_code=404, detail="Course not found or not owned by this student")
    
    # db.add(task)
    # db.commit()
    # db.refresh(task)
    
    # return task
    raise HTTPException(status_code=501, detail="Academic task creation not implemented yet")

# ---- Calendar Events ----
@router.get("/calendar-events", operation_id="get_calendar_events")
async def get_calendar_events(
    current_student: Student = Depends(get_current_student),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get all calendar events for the current student between start date and end date"""
    if start_date is None:
        start_date = datetime.now()
    if end_date is None:
        end_date = start_date + timedelta(days=7)
    # Ensure start_date is before end_date
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    # Fetch calendar events for the current student
    events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == current_student.student_id,
        CalendarEvent.start_time >= start_date,
        CalendarEvent.end_time <= end_date
    ).order_by(CalendarEvent.start_time).all()
    return events

@router.get("/calendar-events/{event_id}", operation_id="get_calendar_event")
async def get_calendar_event(
    event_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get a specific calendar event by ID"""
    db_event = db.query(CalendarEvent).filter(
        CalendarEvent.event_id == event_id,
        CalendarEvent.student_id == current_student.student_id
    ).first()
    
    if not db_event:
        raise HTTPException(status_code=404, detail="Calendar event not found or not owned by this student")
    
    return db_event