from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional
from sqlalchemy import func
import os
from dotenv import load_dotenv
import datetime
import logging
from app.database import SessionLocal, engine
from app.models.reflected_models import Course, Student, StudentCourse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp_server = FastMCP("Planner AI")

# Helper function to get a database session
def get_db_session():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Add a dynamic greeting resource
@mcp_server.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

# Course management tools
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
    Add a new course to the system
    
    Args:
        course_code: Course code (e.g., "CS101")
        course_name: Full name of the course
        course_CRN: Unique Course Registration Number
        course_section: Section number (default: 1)
        course_credits: Number of credits (default: 3)
        actual_enrollment: Current number of students (default: 0) 
        max_enrollment: Maximum enrollment capacity (default: 100)
        instructor: Course instructor name
        semester: Academic semester (default: "Summer 2024-2025")
        timetable: JSON object with course schedule
        
    Returns:
        The newly created course details
    """
    db = get_db_session()
    
    # Check if course with same CRN already exists
    existing_course = db.query(Course).filter(Course.course_CRN == course_CRN).first()
    if existing_course:
        db.close()
        raise ValueError(f"Course with CRN {course_CRN} already exists")
    
    # Default timetable structure if none provided
    if timetable is None:
        timetable = {
            "times": [
                {
                    "days": "MWF",
                    "start_time": "10:00",
                    "end_time": "11:15",
                    "location": "Main Building Room 101"
                }
            ]
        }
    
    # Create new course
    new_course = Course(
        course_code=course_code,
        course_name=course_name,
        course_CRN=course_CRN,
        course_section=course_section,
        course_credits=course_credits,
        actual_enrollment=actual_enrollment,
        max_enrollment=max_enrollment,
        instructor=instructor,
        semester=semester,
        timetable=timetable
    )
    
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    # Convert to dictionary for return
    course_dict = {
        "course_id": new_course.course_id,
        "course_code": new_course.course_code,
        "course_name": new_course.course_name,
        "course_CRN": new_course.course_CRN,
        "course_section": new_course.course_section,
        "course_credits": new_course.course_credits,
        "actual_enrollment": new_course.actual_enrollment,
        "max_enrollment": new_course.max_enrollment,
        "instructor": new_course.instructor,
        "semester": new_course.semester,
        "timetable": new_course.timetable
    }
    
    db.close()
    return course_dict


@mcp_server.tool()
def list_courses(semester: Optional[str] = "Summer 2024-2025") -> List[Dict]:
    """
    List all courses in the system, optionally filtered by semester
    
    Args:
        semester: Optional semester filter (e.g., "Summer 2024-2025")
        
    Returns:
        List of courses
    """
    db = get_db_session()
    
    query = db.query(Course)
    if semester:
        query = query.filter(Course.semester.like(f"%{semester}%"))
    
    courses = query.all()
    
    # Convert to list of dictionaries
    courses_list = []
    for course in courses:
        courses_list.append({
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "course_CRN": course.course_CRN,
            "course_section": course.course_section,
            "course_credits": course.course_credits,
            "actual_enrollment": course.actual_enrollment,
            "max_enrollment": course.max_enrollment,
            "instructor": course.instructor,
            "semester": course.semester,
            "timetable": course.timetable
        })
    
    db.close()
    return courses_list


@mcp_server.tool()
def get_course(course_id: int) -> Dict:
    """
    Get details for a specific course
    
    Args:
        course_id: The course ID to look up
        
    Returns:
        Course details
    """
    db = get_db_session()
    
    course = db.query(Course).filter(Course.course_id == course_id).first()
    if not course:
        db.close()
        raise ValueError(f"Course with ID {course_id} not found")
    
    # Convert to dictionary
    course_dict = {
        "course_id": course.course_id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "course_CRN": course.course_CRN,
        "course_section": course.course_section,
        "course_credits": course.course_credits,
        "actual_enrollment": course.actual_enrollment,
        "max_enrollment": course.max_enrollment,
        "instructor": course.instructor,
        "semester": course.semester,
        "timetable": course.timetable
    }
    
    db.close()
    return course_dict


@mcp_server.tool()
def search_courses(query: str, semester: Optional[str] = "Summer 2024-2025") -> List[Dict]:
    """
    Search for courses by name or code
    
    Args:
        query: Search query string
        semester: Optional semester filter
        
    Returns:
        List of matching courses
    """
    db = get_db_session()
    
    search = f"%{query}%"
    course_query = db.query(Course).filter(
        (func.lower(Course.course_name).like(func.lower(search))) | 
        (func.lower(Course.course_code).like(func.lower(search)))
    )
    
    if semester:
        course_query = course_query.filter(Course.semester.like(f"%{semester}%"))
    
    courses = course_query.all()
    
    # Convert to list of dictionaries
    courses_list = []
    for course in courses:
        courses_list.append({
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "course_CRN": course.course_CRN,
            "course_section": course.course_section,
            "course_credits": course.course_credits,
            "actual_enrollment": course.actual_enrollment,
            "max_enrollment": course.max_enrollment,
            "instructor": course.instructor,
            "semester": course.semester,
            "timetable": course.timetable
        })
    
    db.close()
    return courses_list