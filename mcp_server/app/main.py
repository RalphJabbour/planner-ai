from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional
from sqlalchemy import func
import os
from dotenv import load_dotenv
import datetime
import logging
from app.database import SessionLocal, engine
from app.models.reflected_models import Course, Student, StudentCourse
from app.auth import get_current_student_from_token

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
    token: Optional[str] = None,
    course_code: str = None,
    course_name: str = None,
    course_CRN: int = None,
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
        token: Authorization token (bearer token)
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
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is adding course {course_code}")
        
        # Check if course with same CRN already exists
        existing_course = db.query(Course).filter(Course.course_CRN == course_CRN).first()
        if existing_course:
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
        
        return course_dict
    finally:
        db.close()


@mcp_server.tool()
def list_courses(
    token: Optional[str] = None,
    semester: Optional[str] = "Summer 2024-2025"
) -> List[Dict]:
    """
    List all courses in the system, optionally filtered by semester
    
    Args:
        token: Authorization token (bearer token)
        semester: Optional semester filter (e.g., "Summer 2024-2025")
        
    Returns:
        List of courses
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is listing courses")
        
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
        
        return courses_list
    finally:
        db.close()


@mcp_server.tool()
def get_course(
    token: Optional[str] = None,
    course_id: int = None
) -> Dict:
    """
    Get details for a specific course
    
    Args:
        token: Authorization token (bearer token)
        course_id: The course ID to look up
        
    Returns:
        Course details
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is getting course {course_id}")
        
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
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
        
        return course_dict
    finally:
        db.close()


@mcp_server.tool()
def search_courses(
    token: Optional[str] = None,
    query: str = None, 
    semester: Optional[str] = "Summer 2024-2025"
) -> List[Dict]:
    """
    Search for courses by name or code
    
    Args:
        token: Authorization token (bearer token)
        query: Search query string
        semester: Optional semester filter
        
    Returns:
        List of matching courses
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is searching courses with query: {query}")
        
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
        
        return courses_list
    finally:
        db.close()

# Student-specific tools
@mcp_server.tool()
def get_student_courses(
    token: Optional[str] = None
) -> List[Dict]:
    """
    Get all courses for the current authenticated student
    
    Args:
        token: Authorization token (bearer token)
        
    Returns:
        List of courses the student is registered for
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is retrieving their courses")
        
        # Query to get all courses for this student
        student_courses = db.query(Course).join(
            StudentCourse, Course.course_id == StudentCourse.course_id
        ).filter(
            StudentCourse.student_id == student.student_id
        ).all()
        
        # Convert to list of dictionaries
        courses_list = []
        for course in student_courses:
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
        
        return courses_list
    finally:
        db.close()

@mcp_server.tool()
def register_for_course(
    token: Optional[str] = None,
    course_id: int = None
) -> Dict:
    """
    Register the current student for a course
    
    Args:
        token: Authorization token (bearer token)
        course_id: ID of the course to register for
        
    Returns:
        Registration confirmation
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is registering for course {course_id}")
        
        # Check if course exists
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
        
        # Check if student is already registered
        existing_registration = db.query(StudentCourse).filter(
            StudentCourse.student_id == student.student_id,
            StudentCourse.course_id == course_id
        ).first()
        
        if existing_registration:
            raise ValueError(f"Already registered for course {course.course_code}")
        
        # Register for the course
        new_registration = StudentCourse(
            student_id=student.student_id,
            course_id=course_id
        )
        
        db.add(new_registration)
        
        # Update enrollment count
        course.actual_enrollment += 1
        
        db.commit()
        
        return {
            "message": f"Successfully registered for {course.course_code}",
            "course_id": course_id,
            "course_code": course.course_code,
            "course_name": course.course_name
        }
    finally:
        db.close()

@mcp_server.tool()
def drop_course(
    token: Optional[str] = None,
    course_id: int = None
) -> Dict:
    """
    Drop a course the student is registered for
    
    Args:
        token: Authorization token (bearer token)
        course_id: ID of the course to drop
        
    Returns:
        Confirmation of course drop
    """
    db = get_db_session()
    
    try:
        # Get current authenticated student
        student = get_current_student_from_token(token, db)
        logger.info(f"User {student.name} (ID: {student.student_id}) is dropping course {course_id}")
        
        # Check if course exists
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
        
        # Check if student is registered
        registration = db.query(StudentCourse).filter(
            StudentCourse.student_id == student.student_id,
            StudentCourse.course_id == course_id
        ).first()
        
        if not registration:
            raise ValueError(f"Not registered for course {course.course_code}")
        
        # Drop the course
        db.delete(registration)
        
        # Update enrollment count
        if course.actual_enrollment > 0:
            course.actual_enrollment -= 1
        
        db.commit()
        
        return {
            "message": f"Successfully dropped {course.course_code}",
            "course_id": course_id,
            "course_code": course.course_code,
            "course_name": course.course_name
        }
    finally:
        db.close()