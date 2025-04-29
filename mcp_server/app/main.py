from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional, Any # Added Any
from sqlalchemy import func, delete # Added delete
from sqlalchemy.orm import Session # Added Session
import os
from dotenv import load_dotenv
import datetime # Added datetime
import logging
from app.database import SessionLocal, engine
# Use reflected models
from app.models.reflected_models import (
    Course, Student, StudentCourse, FixedObligation, FlexibleObligation,
    AcademicTask, CalendarEvent
)
# Import necessary schemas or redefine simplified versions for input validation if needed
# For simplicity, we'll use basic types and Dicts for input/output here.
# Complex inputs might require defining Pydantic models within this file or importing them.
from pydantic import BaseModel # Added BaseModel
from datetime import time, date, timedelta # Added time, date, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp_server = FastMCP("Planner AI")

# Helper function to get a database session
def get_db_session() -> Session: # Added type hint
    db = SessionLocal()
    # The original function didn't close the session, which is risky.
    # Using a try/finally block is better practice for tools.
    return db
    # Usage: db = get_db_session(); try: ... finally: db.close()

# --- Schemas (Simplified for Tool Inputs) ---
# Redefine necessary input structures if complex validation is needed
# Otherwise, rely on type hints in function arguments.

class FixedObligationInput(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: time
    end_time: time
    days_of_week: List[str] # e.g., ["Monday", "Wednesday"]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    recurrence: Optional[str] = "weekly"
    priority: Optional[int] = 3
    location: Optional[str] = None
    course_id: Optional[int] = None # Link to course if applicable

class FlexibleObligationInput(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: int
    total_hours_required: float
    deadline: Optional[datetime.datetime] = None
    preferred_start_time: Optional[time] = None
    preferred_end_time: Optional[time] = None
    hours_per_session: Optional[float] = None
    sessions_per_week: Optional[int] = None
    specific_days: Optional[List[str]] = None # e.g., ["Monday", "Friday"]
    course_id: Optional[int] = None # Link to course if applicable

class AcademicTaskInput(BaseModel):
    course_id: int
    task_type: str # e.g., "assignment", "exam", "project"
    name: str
    description: Optional[str] = None
    due_date: datetime.datetime
    estimated_effort_hours: Optional[float] = None
    priority: Optional[int] = 2 # Default priority

# --- Helper Functions (Potentially needed from backend logic) ---

def get_time(time_str: Optional[str]) -> Optional[time]:
    if not time_str:
        return None
    try:
        return datetime.datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        try:
            # Handle ISO format like "HH:MM:SS" if needed
            return datetime.datetime.strptime(time_str, '%H:%M:%S').time()
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            return None

def get_start_end_date(semester: str) -> tuple[Optional[date], Optional[date]]:
    # Simplified logic - replace with actual backend logic if available
    # This needs to be robust based on how semesters are defined
    year_part = semester.split()[-1]
    term = semester.split()[0]
    try:
        start_year = int(year_part.split('-')[0])
        end_year = int(year_part.split('-')[1])
        if term.lower() == "fall":
            return date(start_year, 8, 15), date(start_year, 12, 20)
        elif term.lower() == "spring":
            return date(end_year, 1, 15), date(end_year, 5, 20)
        elif term.lower() == "summer":
            return date(end_year, 6, 1), date(end_year, 8, 10)
    except Exception as e:
        logger.error(f"Could not parse semester '{semester}': {e}")
    return None, None

def create_calendar_events_from_fixed(
    fixed_obligation: FixedObligation,
    student_id: int, # Changed from Student object
    db: Session
):
    """Creates recurring calendar events based on a FixedObligation."""
    if not fixed_obligation.start_date or not fixed_obligation.end_date or not fixed_obligation.days_of_week:
        logger.warning(f"Fixed obligation {fixed_obligation.obligation_id} missing required date/day info for event creation.")
        return

    current_date = fixed_obligation.start_date
    end_date = fixed_obligation.end_date
    days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    target_weekdays = {days_map[day] for day in fixed_obligation.days_of_week if day in days_map}

    if not target_weekdays:
        logger.warning(f"No valid days specified for fixed obligation {fixed_obligation.obligation_id}")
        return

    events_created = 0
    while current_date <= end_date:
        if current_date.weekday() in target_weekdays:
            start_datetime = datetime.datetime.combine(current_date, fixed_obligation.start_time)
            end_datetime = datetime.datetime.combine(current_date, fixed_obligation.end_time)

            # Check if event already exists for this exact time to avoid duplicates
            exists = db.query(CalendarEvent).filter(
                CalendarEvent.student_id == student_id,
                CalendarEvent.fixed_obligation_id == fixed_obligation.obligation_id,
                CalendarEvent.start_time == start_datetime
            ).first()

            if not exists:
                new_event = CalendarEvent(
                    student_id=student_id,
                    fixed_obligation_id=fixed_obligation.obligation_id,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    event_type="fixed_obligation",
                    is_recurring=True,
                    recurrence_pattern=fixed_obligation.recurrence,
                    location=fixed_obligation.location
                )
                db.add(new_event)
                events_created += 1

        current_date += timedelta(days=1)

    if events_created > 0:
        try:
            db.commit()
            logger.info(f"Created {events_created} calendar events for fixed obligation {fixed_obligation.obligation_id}.")
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing calendar events for fixed obligation {fixed_obligation.obligation_id}: {e}")
    else:
        logger.info(f"No new calendar events needed for fixed obligation {fixed_obligation.obligation_id}.")


# --- Existing Tools (add_course, list_courses, get_course, search_courses) ---
# These seem okay, but ensure they use try/finally for db.close()

@mcp_server.tool()
def add_course(
    course_code: str,
    course_name: str,
    course_CRN: int,
    course_section: int = 1,
    course_credits: int = 3,
    actual_enrollment: int = 0,
    max_enrollment: int = 100,
    instructor: Optional[str] = None,
    semester: str = "Summer 2024-2025",
    timetable: Optional[Dict] = None
) -> Dict:
    """
    Add a new course to the system.
    Args are the same as before.
    Returns the newly created course details.
    """
    db = get_db_session()
    try:
        existing_course = db.query(Course).filter(Course.course_CRN == course_CRN).first()
        if existing_course:
            raise ValueError(f"Course with CRN {course_CRN} already exists")

        if timetable is None:
            timetable = {
                "times": [{"days": "MWF", "start_time": "10:00", "end_time": "11:15", "location": "TBA"}]
            }

        new_course = Course(
            course_code=course_code, course_name=course_name, course_CRN=course_CRN,
            course_section=course_section, course_credits=course_credits,
            actual_enrollment=actual_enrollment, max_enrollment=max_enrollment,
            instructor=instructor, semester=semester, timetable=timetable
        )
        db.add(new_course)
        db.commit()
        db.refresh(new_course)

        course_dict = {c.name: getattr(new_course, c.name) for c in new_course.__table__.columns}
        return course_dict
    except Exception as e:
        db.rollback() # Rollback on error
        logger.error(f"Error adding course: {e}")
        raise # Re-raise the exception
    finally:
        db.close()


@mcp_server.tool()
def list_courses(semester: Optional[str] = "Summer 2024-2025") -> List[Dict]:
    """
    List all courses in the system, optionally filtered by semester.
    Args: semester (Optional semester filter).
    Returns: List of courses.
    """
    db = get_db_session()
    try:
        query = db.query(Course)
        if semester:
            query = query.filter(Course.semester.like(f"%{semester}%"))
        courses = query.all()
        courses_list = [{c.name: getattr(course, c.name) for c in course.__table__.columns} for course in courses]
        return courses_list
    finally:
        db.close()


@mcp_server.tool()
def get_course(course_id: int) -> Dict:
    """
    Get details for a specific course.
    Args: course_id (The course ID).
    Returns: Course details.
    """
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
        course_dict = {c.name: getattr(course, c.name) for c in course.__table__.columns}
        return course_dict
    finally:
        db.close()


@mcp_server.tool()
def search_courses(query: str, semester: Optional[str] = "Summer 2024-2025") -> List[Dict]:
    """
    Search for courses by name or code.
    Args: query (Search string), semester (Optional semester filter).
    Returns: List of matching courses.
    """
    db = get_db_session()
    try:
        search = f"%{query}%"
        course_query = db.query(Course).filter(
            (func.lower(Course.course_name).like(func.lower(search))) |
            (func.lower(Course.course_code).like(func.lower(search)))
        )
        if semester:
            course_query = course_query.filter(Course.semester.like(f"%{semester}%"))
        courses = course_query.all()
        courses_list = [{c.name: getattr(course, c.name) for c in course.__table__.columns} for course in courses]
        return courses_list
    finally:
        db.close()


# --- New Tools from Backend Routers ---

# == Courses Router ==

@mcp_server.tool()
def register_course(student_id: int, course_id: int) -> Dict:
    """
    Register a student for a specific course and create corresponding fixed obligations/calendar events.
    Args:
        student_id: The ID of the student.
        course_id: The ID of the course to register for.
    Returns:
        Success message or error details.
    """
    db = get_db_session()
    try:
        # Check if student exists
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise ValueError(f"Student with ID {student_id} not found")

        # Check if course exists
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")

        # Check if already registered
        existing_registration = db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.course_id == course_id
        ).first()
        if existing_registration:
            raise ValueError("Student already registered for this course")

        # Create registration
        new_registration = StudentCourse(student_id=student_id, course_id=course_id)
        db.add(new_registration)
        db.commit()
        logger.info(f"Student {student_id} registered for course {course_id}")

        # Create Fixed Obligations based on timetable
        created_obligations = []
        recurrences = course.timetable.get("times", []) if course.timetable else []
        for recurrence in recurrences:
            start_time = get_time(recurrence.get("start_time"))
            end_time = get_time(recurrence.get("end_time"))
            start_date, end_date = get_start_end_date(course.semester)

            if not start_time or not end_time or not start_date or not end_date:
                logger.warning(f"Skipping obligation creation for course {course_id} due to invalid time/date: {recurrence}")
                continue

            days_string = recurrence.get("days", "")
            days_of_week = []
            for char in days_string:
                day_map = {'M': "Monday", 'T': "Tuesday", 'W': "Wednesday", 'R': "Thursday", 'F': "Friday", 'S': "Saturday", 'U': "Sunday"}
                if char in day_map:
                    days_of_week.append(day_map[char])

            if not days_of_week:
                logger.warning(f"Skipping obligation for course {course_id}, no valid days found in '{days_string}'")
                continue

            new_obligation = FixedObligation(
                student_id=student_id,
                name=course.course_name,
                description=f"{course.course_code} Lecture/Lab",
                start_time=start_time,
                end_time=end_time,
                days_of_week=days_of_week,
                start_date=start_date,
                end_date=end_date,
                recurrence="weekly",
                priority=3, # Default priority for courses
                course_id=course.course_id,
                location=recurrence.get("location")
            )
            db.add(new_obligation)
            db.commit() # Commit each obligation to get its ID for event creation
            db.refresh(new_obligation)
            created_obligations.append(new_obligation.obligation_id)
            logger.info(f"Created fixed obligation {new_obligation.obligation_id} for student {student_id}, course {course_id}")

            # Create calendar events for this obligation
            create_calendar_events_from_fixed(new_obligation, student_id, db)

        # TODO: Add call to schedule optimizer if needed (e.g., call an update_schedule tool)

        return {"message": "Course registered successfully", "created_obligation_ids": created_obligations}

    except Exception as e:
        db.rollback()
        logger.error(f"Error registering course {course_id} for student {student_id}: {e}")
        # Raise a more specific error or return an error dict
        raise ValueError(f"Failed to register course: {e}")
    finally:
        db.close()


@mcp_server.tool()
def get_registered_courses(student_id: int) -> List[Dict]:
    """
    Get all courses registered by a specific student.
    Args:
        student_id: The ID of the student.
    Returns:
        List of registered course details.
    """
    db = get_db_session()
    try:
        registrations = db.query(Course).join(StudentCourse).filter(StudentCourse.student_id == student_id).all()
        courses_list = [{c.name: getattr(course, c.name) for c in course.__table__.columns} for course in registrations]
        return courses_list
    finally:
        db.close()


@mcp_server.tool()
def unregister_course(student_id: int, course_id: int) -> Dict:
    """
    Unregister a student from a course and remove associated fixed obligations/calendar events.
    Args:
        student_id: The ID of the student.
        course_id: The ID of the course to unregister from.
    Returns:
        Success message or error details.
    """
    db = get_db_session()
    try:
        # Find registration
        registration = db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.course_id == course_id
        ).first()

        if not registration:
            raise ValueError("Student is not registered for this course")

        # Find and delete associated fixed obligations and their calendar events
        obligations_to_delete = db.query(FixedObligation).filter(
            FixedObligation.student_id == student_id,
            FixedObligation.course_id == course_id
        ).all()

        deleted_obligation_ids = []
        for obligation in obligations_to_delete:
            obligation_id = obligation.obligation_id
            # Delete associated calendar events first
            db.execute(delete(CalendarEvent).where(CalendarEvent.fixed_obligation_id == obligation_id))
            db.delete(obligation)
            deleted_obligation_ids.append(obligation_id)
            logger.info(f"Deleted fixed obligation {obligation_id} and its events for student {student_id}, course {course_id}")

        # Delete the registration
        db.delete(registration)
        db.commit()
        logger.info(f"Student {student_id} unregistered from course {course_id}")

        # TODO: Add call to schedule optimizer if needed

        return {"message": "Course unregistered successfully", "deleted_obligation_ids": deleted_obligation_ids}
    except Exception as e:
        db.rollback()
        logger.error(f"Error unregistering course {course_id} for student {student_id}: {e}")
        raise ValueError(f"Failed to unregister course: {e}")
    finally:
        db.close()


# == Tasks Router ==

@mcp_server.tool()
def create_fixed_obligation(student_id: int, obligation_data: Dict) -> Dict:
    """
    Create a new fixed obligation (non-course related) for a student and associated calendar events.
    Args:
        student_id: The ID of the student.
        obligation_data: A dictionary containing obligation details (name, start_time, end_time, days_of_week, etc., matching FixedObligationInput).
    Returns:
        Details of the created obligation or error message.
    """
    db = get_db_session()
    try:
        # Validate input data (basic example)
        try:
            validated_data = FixedObligationInput(**obligation_data)
        except Exception as e:
             raise ValueError(f"Invalid obligation data format: {e}")

        new_obligation = FixedObligation(
            student_id=student_id,
            **validated_data.model_dump(exclude_unset=True) # Use validated data
        )
        db.add(new_obligation)
        db.commit()
        db.refresh(new_obligation)
        logger.info(f"Created fixed obligation {new_obligation.obligation_id} for student {student_id}")

        # Create calendar events
        create_calendar_events_from_fixed(new_obligation, student_id, db)

        # TODO: Add call to schedule optimizer if needed

        obligation_dict = {c.name: getattr(new_obligation, c.name) for c in new_obligation.__table__.columns}
        return {"message": "Fixed obligation created successfully", "obligation": obligation_dict}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating fixed obligation for student {student_id}: {e}")
        raise ValueError(f"Failed to create fixed obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def get_fixed_obligations(student_id: int) -> List[Dict]:
    """
    Get all fixed obligations for a specific student.
    Args:
        student_id: The ID of the student.
    Returns:
        List of fixed obligations.
    """
    db = get_db_session()
    try:
        obligations = db.query(FixedObligation).filter(FixedObligation.student_id == student_id).all()
        obligations_list = [{c.name: getattr(ob, c.name) for c in ob.__table__.columns} for ob in obligations]
        return obligations_list
    finally:
        db.close()


@mcp_server.tool()
def update_fixed_obligation(student_id: int, obligation_id: int, update_data: Dict) -> Dict:
    """
    Update an existing fixed obligation for a student. Note: This might require deleting and recreating calendar events.
    Args:
        student_id: The ID of the student.
        obligation_id: The ID of the obligation to update.
        update_data: Dictionary with fields to update.
    Returns:
        Details of the updated obligation or error message.
    """
    db = get_db_session()
    try:
        obligation = db.query(FixedObligation).filter(
            FixedObligation.obligation_id == obligation_id,
            FixedObligation.student_id == student_id
        ).first()

        if not obligation:
            raise ValueError(f"Fixed obligation with ID {obligation_id} not found for student {student_id}")

        # Basic update - more complex updates (like changing recurrence) require event handling
        for key, value in update_data.items():
             # Add validation: check if key is a valid attribute and potentially parse/validate value
             if hasattr(obligation, key):
                 # Special handling for time/date if needed
                 if key in ['start_time', 'end_time'] and isinstance(value, str):
                     setattr(obligation, key, get_time(value))
                 elif key in ['start_date', 'end_date'] and isinstance(value, str):
                     setattr(obligation, key, datetime.datetime.strptime(value, '%Y-%m-%d').date())
                 else:
                     setattr(obligation, key, value)
             else:
                 logger.warning(f"Ignoring invalid field in update_data: {key}")


        # **Important**: If time, date, or days_of_week changed, delete old events and recreate
        # This logic can be complex, simplified here
        # if any(k in update_data for k in ['start_time', 'end_time', 'days_of_week', 'start_date', 'end_date']):
        #     logger.info(f"Recurrence changed for obligation {obligation_id}, recreating calendar events.")
        #     db.execute(delete(CalendarEvent).where(CalendarEvent.fixed_obligation_id == obligation_id))
        #     # Commit deletion before creating new ones if necessary
        #     db.commit()
        #     create_calendar_events_from_fixed(obligation, student_id, db) # Pass the updated obligation
        # else:
        #     db.commit() # Commit simple updates

        db.commit() # Commit updates (event recreation needs more robust handling)
        db.refresh(obligation)
        logger.info(f"Updated fixed obligation {obligation_id} for student {student_id}")

        # TODO: Add call to schedule optimizer if needed

        obligation_dict = {c.name: getattr(obligation, c.name) for c in obligation.__table__.columns}
        return {"message": "Fixed obligation updated successfully", "obligation": obligation_dict}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating fixed obligation {obligation_id} for student {student_id}: {e}")
        raise ValueError(f"Failed to update fixed obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def delete_fixed_obligation(student_id: int, obligation_id: int) -> Dict:
    """
    Delete a fixed obligation and its associated calendar events.
    Args:
        student_id: The ID of the student.
        obligation_id: The ID of the obligation to delete.
    Returns:
        Success message or error details.
    """
    db = get_db_session()
    try:
        obligation = db.query(FixedObligation).filter(
            FixedObligation.obligation_id == obligation_id,
            FixedObligation.student_id == student_id
        ).first()

        if not obligation:
            raise ValueError(f"Fixed obligation with ID {obligation_id} not found for student {student_id}")

        # Delete associated calendar events first
        deleted_events_count = db.execute(delete(CalendarEvent).where(CalendarEvent.fixed_obligation_id == obligation_id)).rowcount
        logger.info(f"Deleted {deleted_events_count} calendar events for fixed obligation {obligation_id}")

        # Delete the obligation
        db.delete(obligation)
        db.commit()
        logger.info(f"Deleted fixed obligation {obligation_id} for student {student_id}")

        # TODO: Add call to schedule optimizer if needed

        return {"message": "Fixed obligation deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting fixed obligation {obligation_id} for student {student_id}: {e}")
        raise ValueError(f"Failed to delete fixed obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def create_flexible_obligation(student_id: int, obligation_data: Dict) -> Dict:
    """
    Create a new flexible obligation for a student.
    Args:
        student_id: The ID of the student.
        obligation_data: Dictionary with flexible obligation details (name, priority, total_hours_required, etc., matching FlexibleObligationInput).
    Returns:
        Details of the created flexible obligation or error message.
    """
    db = get_db_session()
    try:
        # Validate input data
        try:
            validated_data = FlexibleObligationInput(**obligation_data)
        except Exception as e:
             raise ValueError(f"Invalid obligation data format: {e}")

        new_obligation = FlexibleObligation(
            student_id=student_id,
            **validated_data.model_dump(exclude_unset=True)
        )
        db.add(new_obligation)
        db.commit()
        db.refresh(new_obligation)
        logger.info(f"Created flexible obligation {new_obligation.obligation_id} for student {student_id}")

        # TODO: Add call to schedule optimizer is CRUCIAL here

        obligation_dict = {c.name: getattr(new_obligation, c.name) for c in new_obligation.__table__.columns}
        return {"message": "Flexible obligation created successfully", "obligation": obligation_dict}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating flexible obligation for student {student_id}: {e}")
        raise ValueError(f"Failed to create flexible obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def get_flexible_obligations(student_id: int) -> List[Dict]:
    """
    Get all flexible obligations for a specific student.
    Args:
        student_id: The ID of the student.
    Returns:
        List of flexible obligations.
    """
    db = get_db_session()
    try:
        obligations = db.query(FlexibleObligation).filter(FlexibleObligation.student_id == student_id).all()
        obligations_list = [{c.name: getattr(ob, c.name) for c in ob.__table__.columns} for ob in obligations]
        return obligations_list
    finally:
        db.close()


@mcp_server.tool()
def update_flexible_obligation(student_id: int, obligation_id: int, update_data: Dict) -> Dict:
    """
    Update an existing flexible obligation for a student.
    Args:
        student_id: The ID of the student.
        obligation_id: The ID of the obligation to update.
        update_data: Dictionary with fields to update.
    Returns:
        Details of the updated obligation or error message.
    """
    db = get_db_session()
    try:
        obligation = db.query(FlexibleObligation).filter(
            FlexibleObligation.obligation_id == obligation_id,
            FlexibleObligation.student_id == student_id
        ).first()

        if not obligation:
            raise ValueError(f"Flexible obligation with ID {obligation_id} not found for student {student_id}")

        for key, value in update_data.items():
             if hasattr(obligation, key):
                 # Add type validation/conversion if necessary
                 setattr(obligation, key, value)
             else:
                 logger.warning(f"Ignoring invalid field in update_data: {key}")

        db.commit()
        db.refresh(obligation)
        logger.info(f"Updated flexible obligation {obligation_id} for student {student_id}")

        # TODO: Add call to schedule optimizer is CRUCIAL here

        obligation_dict = {c.name: getattr(obligation, c.name) for c in obligation.__table__.columns}
        return {"message": "Flexible obligation updated successfully", "obligation": obligation_dict}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating flexible obligation {obligation_id} for student {student_id}: {e}")
        raise ValueError(f"Failed to update flexible obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def delete_flexible_obligation(student_id: int, obligation_id: int) -> Dict:
    """
    Delete a flexible obligation and potentially its associated scheduled calendar events.
    Args:
        student_id: The ID of the student.
        obligation_id: The ID of the obligation to delete.
    Returns:
        Success message or error details.
    """
    db = get_db_session()
    try:
        obligation = db.query(FlexibleObligation).filter(
            FlexibleObligation.obligation_id == obligation_id,
            FlexibleObligation.student_id == student_id
        ).first()

        if not obligation:
            raise ValueError(f"Flexible obligation with ID {obligation_id} not found for student {student_id}")

        # Delete associated calendar events (events specifically scheduled for this flex task)
        deleted_events_count = db.execute(delete(CalendarEvent).where(
            CalendarEvent.flexible_obligation_id == obligation_id
        )).rowcount
        logger.info(f"Deleted {deleted_events_count} calendar events for flexible obligation {obligation_id}")

        # Delete the obligation
        db.delete(obligation)
        db.commit()
        logger.info(f"Deleted flexible obligation {obligation_id} for student {student_id}")

        # TODO: Add call to schedule optimizer is CRUCIAL here

        return {"message": "Flexible obligation deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting flexible obligation {obligation_id} for student {student_id}: {e}")
        raise ValueError(f"Failed to delete flexible obligation: {e}")
    finally:
        db.close()


@mcp_server.tool()
def create_academic_task(student_id: int, task_data: Dict) -> Dict:
    """
    Create a new academic task (exam, assignment, project) for a student, linked to a course.
    Args:
        student_id: The ID of the student.
        task_data: Dictionary with task details (course_id, task_type, name, due_date, etc., matching AcademicTaskInput).
    Returns:
        Details of the created academic task or error message.
    """
    db = get_db_session()
    try:
        # Validate input data
        try:
            validated_data = AcademicTaskInput(**task_data)
        except Exception as e:
             raise ValueError(f"Invalid task data format: {e}")

        # Check if student is registered for the course
        is_registered = db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.course_id == validated_data.course_id
        ).first()
        if not is_registered:
            raise ValueError("Student is not registered for this course")

        new_task = AcademicTask(
            student_id=student_id,
            **validated_data.model_dump(exclude_unset=True)
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        logger.info(f"Created academic task {new_task.task_id} for student {student_id}")

        # Academic tasks often become flexible obligations implicitly or explicitly
        # Consider creating a corresponding FlexibleObligation here if needed by the optimizer
        # E.g., create_flexible_obligation(student_id, {"name": new_task.name, ...})

        # TODO: Add call to schedule optimizer if needed

        task_dict = {c.name: getattr(new_task, c.name) for c in new_task.__table__.columns}
        return {"message": "Academic task created successfully", "task": task_dict}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating academic task for student {student_id}: {e}")
        raise ValueError(f"Failed to create academic task: {e}")
    finally:
        db.close()


@mcp_server.tool()
def get_academic_tasks(student_id: int, course_id: Optional[int] = None) -> List[Dict]:
    """
    Get academic tasks for a student, optionally filtered by course.
    Args:
        student_id: The ID of the student.
        course_id: Optional ID of the course to filter by.
    Returns:
        List of academic tasks.
    """
    db = get_db_session()
    try:
        query = db.query(AcademicTask).filter(AcademicTask.student_id == student_id)
        if course_id:
            query = query.filter(AcademicTask.course_id == course_id)
        tasks = query.order_by(AcademicTask.due_date).all()
        tasks_list = [{c.name: getattr(task, c.name) for c in task.__table__.columns} for task in tasks]
        return tasks_list
    finally:
        db.close()


@mcp_server.tool()
def get_calendar_events(student_id: int, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> List[Dict]:
    """
    Get calendar events for a student within a specified date range.
    Args:
        student_id: The ID of the student.
        start_date_str: Optional start date string (YYYY-MM-DD). Defaults to today.
        end_date_str: Optional end date string (YYYY-MM-DD). Defaults to 7 days from start date.
    Returns:
        List of calendar events with associated obligation names.
    """
    db = get_db_session()
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.datetime.now()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else start_date + timedelta(days=7)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)


        if start_date >= end_date:
             raise ValueError("Start date must be before end date")

        events = db.query(CalendarEvent).filter(
            CalendarEvent.student_id == student_id,
            CalendarEvent.start_time < end_date,
            CalendarEvent.end_time > start_date
        ).order_by(CalendarEvent.start_time).all()

        events_with_details = []
        for event in events:
            obligation_name = "Unknown Event"
            obligation_type = "unknown"
            obligation_id = None

            if event.fixed_obligation_id:
                obligation = db.query(FixedObligation.name).filter(FixedObligation.obligation_id == event.fixed_obligation_id).first()
                if obligation:
                    obligation_name = obligation.name
                obligation_type = "fixed"
                obligation_id = event.fixed_obligation_id
            elif event.flexible_obligation_id:
                obligation = db.query(FlexibleObligation.name, FlexibleObligation.description).filter(FlexibleObligation.obligation_id == event.flexible_obligation_id).first()
                if obligation:
                    obligation_name = obligation.name or obligation.description # Fallback to description
                obligation_type = "flexible"
                obligation_id = event.flexible_obligation_id

            event_dict = {c.name: getattr(event, c.name) for c in event.__table__.columns}
            event_dict["name"] = obligation_name
            event_dict["obligation_type"] = obligation_type
            event_dict["obligation_id"] = obligation_id # Add the linked obligation ID
            events_with_details.append(event_dict)

        return events_with_details
    finally:
        db.close()


# == User Router ==

@mcp_server.tool()
def get_user_info(student_id: int) -> Dict:
    """
    Get basic information for a specific student.
    Args:
        student_id: The ID of the student.
    Returns:
        Dictionary containing student information (id, name, email, program, year, preferences).
    """
    db = get_db_session()
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise ValueError(f"Student with ID {student_id} not found")

        user_info = {
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "program": student.program,
            "year": student.year,
            "preferences": student.preferences, # Be cautious about returning sensitive preferences
        }
        return user_info
    finally:
        db.close()


# --- Add OR-Tools Optimizer Tool ---
# This requires understanding how the optimizer is called in the backend
# Assuming it takes student_id and returns updated events

# @mcp_server.tool()
# def optimize_schedule(student_id: int) -> List[Dict]:
#     """
#     Run the schedule optimizer for the given student.
#     Args:
#         student_id: The ID of the student whose schedule needs optimization.
#     Returns:
#         List of updated/scheduled calendar events.
#     """
#     db = get_db_session()
#     try:
#         # This assumes update_schedule function is available and adapted
#         # It might need direct import or reimplementation here
#         # from app.or_tools.service import update_schedule # Needs adaptation
#         # payload = {"student_id": student_id}
#         # updated_events = update_schedule(payload, db) # Call the optimizer logic
#         # logger.info(f"Optimizer run for student {student_id}, returned {len(updated_events)} events.")
#         # return updated_events
#         logger.warning("optimize_schedule tool is not fully implemented yet.")
#         raise NotImplementedError("Schedule optimization tool needs implementation.")
#     except Exception as e:
#         db.rollback() # Ensure rollback if optimizer fails
#         logger.error(f"Error optimizing schedule for student {student_id}: {e}")
#         raise ValueError(f"Failed to optimize schedule: {e}")
#     finally:
#         db.close()


# --- FastAPI App Setup (Keep as is) ---
# This part runs the MCP server itself
# REMOVE OR COMMENT OUT THE LINE BELOW:
# app = mcp_server.build_app() # This line causes the AttributeError

# Example of running with uvicorn if needed directly
# import uvicorn
# if __name__ == "__main__":
#     # If running this file directly, you'd use sse_app() here too
#     # direct_app = mcp_server.sse_app()
#     # uvicorn.run(direct_app, host="0.0.0.0", port=3001)
#     pass # Keep this file focused on defining tools and the mcp_server instance