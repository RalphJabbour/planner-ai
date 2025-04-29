import logging
from typing import List, Dict, Any, Optional
from datetime import time, date, datetime

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session
from app.models.course import Course, StudentCourse
from app.models.schedule import FixedObligation, FlexibleObligation, CalendarEvent
from app.models.student import Student # Needed for type hinting if passing student object
from app.routers.courses import get_start_end_date # Helper function
from app.routers.courses import get_time # Helper

from fastapi import FastAPI, Depends
app = FastAPI()


# --- Database Setup (Manual Session Management) ---
# Adjust imports based on your actual project structure
try:
    from app.database import SessionLocal, get_db # Try importing FastAPI's get_db first
    # If get_db works standalone (unlikely without request context), use it.
    # Otherwise, fall back to manual session creation.
    def get_mcp_db_session() -> Session:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

except ImportError:
    # Fallback if SessionLocal is not directly accessible or needs FastAPI context
    # This assumes your database setup allows creating sessions manually.
    # You might need to adjust this based on your database.py
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@db:5432/EECE503N-planner") # Make sure this matches your env
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_mcp_db_session() -> Session:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

# --- Model Imports ---
# Import necessary models directly

# --- Router Logic Imports (or reimplement core logic here) ---
# It's often cleaner to have service functions separate from routers.
# If not, you might import router functions, but be careful about dependencies.
# For simplicity, we might redefine simplified logic here or call helper functions.
# Example: Importing the function signature might be complex due to FastAPI Depends.
# Let's define helper functions based on router logic.

from app.routers.courses import register_course as register_course_logic # Assuming this can be adapted
from app.routers.tasks import create_fixed_obligation as create_fixed_obligation_logic
from app.routers.tasks import create_flexible_obligation as create_flexible_obligation_logic
# Note: These imports might fail if they rely heavily on FastAPI's Depends.
# We may need to refactor the core logic into separate service functions.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP("PlannerAI_MCP")

# --- Tool Definitions ---

@mcp.tool()
async def find_course(course_code: str, semester: Optional[str] = "Summer 2024-2025") -> List[Dict[str, Any]]:
    """Finds course details by course code and semester."""
    logger.info(f"MCP Tool: find_course called with code={course_code}, semester={semester}")
    courses_found = []
    db_gen = get_mcp_db_session()
    db = next(db_gen)
    try:
        query = db.query(Course).filter(Course.course_code.ilike(f"%{course_code}%"))
        if semester:
            query = query.filter(Course.semester == semester)
        courses = query.limit(5).all() # Limit results
        for course in courses:
            courses_found.append({
                "course_id": course.course_id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "course_CRN": course.course_CRN,
                "semester": course.semester,
                "instructor": course.instructor,
                "timetable": course.timetable,
            })
        logger.info(f"Found {len(courses_found)} courses matching '{course_code}'")
    except Exception as e:
        logger.error(f"Error in find_course: {e}", exc_info=True)
        # Return an empty list or error indicator if preferred
    finally:
        next(db_gen, None) # Ensure session is closed
    return courses_found


@mcp.tool()
async def check_schedule_fit(student_id: int, course_id: int) -> Dict[str, Any]:
    """Checks if a course's schedule conflicts with the student's existing fixed events."""
    logger.info(f"MCP Tool: check_schedule_fit called for student={student_id}, course={course_id}")
    db_gen = get_mcp_db_session()
    db = next(db_gen)
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course or not course.timetable or not course.timetable.get("times"):
            return {"fits": False, "reason": "Course timetable not found or invalid."}

        # Simplified check: Get student's fixed events for the semester timeframe
        # A full check would involve the OR-Tools optimizer logic
        start_date, end_date = get_start_end_date(course.semester)

        existing_events = db.query(CalendarEvent).filter(
            CalendarEvent.student_id == student_id,
            CalendarEvent.event_type == 'fixed_obligation', # Check against fixed events
            CalendarEvent.date >= start_date,
            CalendarEvent.date <= end_date
        ).all()

        # Basic overlap check (placeholder for more complex logic)
        conflicts = []
        days_map = {"M": 0, "T": 1, "W": 2, "R": 3, "F": 4, "S": 5, "U": 6} # Mon=0..Sun=6 mapping might differ

        for recurrence in course.timetable.get("times", []):
            course_start_time = get_time(recurrence.get("start_time"))
            course_end_time = get_time(recurrence.get("end_time"))
            course_days_str = recurrence.get("days", "")

            if not course_start_time or not course_end_time: continue

            course_weekdays = {days_map[day_char] for day_char in course_days_str if day_char in days_map}

            for event in existing_events:
                event_weekday = event.start_time.weekday()
                if event_weekday in course_weekdays:
                    # Check for time overlap on the same day of the week
                    event_start = event.start_time.time()
                    event_end = event.end_time.time()
                    # Overlap condition: (CourseStart < EventEnd) and (CourseEnd > EventStart)
                    if course_start_time < event_end and course_end_time > event_start:
                        conflicts.append(f"Conflicts with existing event on {event.start_time.strftime('%A %H:%M')}")
                        # Simple check: return on first conflict
                        logger.warning(f"Conflict found for course {course_id}: {conflicts[0]}")
                        return {"fits": False, "reason": conflicts[0]}

        logger.info(f"Course {course_id} fits schedule for student {student_id}.")
        return {"fits": True, "reason": "No direct time conflicts found with fixed obligations."}

    except Exception as e:
        logger.error(f"Error in check_schedule_fit: {e}", exc_info=True)
        return {"fits": False, "reason": f"Error during check: {e}"}
    finally:
        next(db_gen, None)

# Note: Directly calling router functions that use FastAPI's Depends() from here
# is problematic. The core logic should ideally be in service functions that
# accept db session and parameters directly.
# For now, these tools might need refactoring of the underlying logic
# or will be placeholders.

@mcp.tool()
async def register_course(student_id: int, course_id: int) -> Dict[str, Any]:
    """Registers a student for a specific course ID. Assumes schedule fit has been checked."""
    logger.info(f"MCP Tool: register_course called for student={student_id}, course={course_id}")
    # This tool *proposes* the action. The actual registration happens
    # after user confirmation via the /chat/confirm endpoint.
    # We just validate the possibility here.
    db_gen = get_mcp_db_session()
    db = next(db_gen)
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            return {"success": False, "message": "Course not found."}

        existing = db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.course_id == course_id
        ).first()
        if existing:
            return {"success": False, "message": "Student already registered."}

        # If validation passes, return success for the proposal stage
        return {"success": True, "message": f"Proposal to register course {course.course_code} created."}
    except Exception as e:
        logger.error(f"Error in register_course tool: {e}", exc_info=True)
        return {"success": False, "message": f"Error during registration check: {e}"}
    finally:
        next(db_gen, None)


# Add more tools as needed (add_fixed_obligation, add_flexible_obligation, etc.)
# following a similar pattern: accept necessary data, perform validation using
# a manual DB session, return success/failure for the *proposal*.

# Example placeholder for adding a flexible obligation
@mcp.tool()
async def add_flexible_obligation(
    student_id: int,
    name: str,
    description: str,
    weekly_target_hours: float,
    priority: int,
    start_date: Optional[str] = None, # Use string for ISO date format
    end_date: Optional[str] = None,   # Use string for ISO date format
    constraints: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Proposes adding a new flexible obligation."""
    logger.info(f"MCP Tool: add_flexible_obligation called for student={student_id}, name={name}")
    # Basic validation
    if not (1 <= priority <= 5):
        return {"success": False, "message": "Priority must be between 1 and 5."}
    if weekly_target_hours <= 0:
        return {"success": False, "message": "Weekly target hours must be positive."}
    # Add date format validation if needed

    # Return success for the proposal
    return {"success": True, "message": f"Proposal to add flexible obligation '{name}' created."}


# --- Mount the MCP SSE app onto the FastAPI app ---
# The path "/mcp" here corresponds to the base URL used by the sse_client
app.mount("/mcp", mcp.sse_app())
logger.info("Mounted MCP SSE app at /mcp")

if __name__ == "__main__":
    import uvicorn
    # --- Run the FastAPI app using Uvicorn ---
    # mcp.run() # DO NOT use this for SSE/HTTP
    print("Starting FastAPI server with Uvicorn on host 0.0.0.0, port 9002...")
    uvicorn.run(
        app, # Run the FastAPI app instance
        host="0.0.0.0", # Host to listen on (0.0.0.0 makes it accessible externally)
        port=9002,      # Port to listen on
        log_level="info"
    )