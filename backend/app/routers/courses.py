import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.auth.token import get_current_student
from app.routers.tasks import create_fixed_obligation, FixedObligationCreate
import datetime
from app.or_tools.service import update_schedule  # Import the update_schedule function

router = APIRouter(prefix="/courses", tags=["courses"])

class CourseRegistration(BaseModel):
    course_id: int

def get_days_array(days):
    result = []
    for day in days:
        if day == "M":
            result.append("Monday")
        elif day == "T":
            result.append("Tuesday")
        elif day == "W":
            result.append("Wednesday")
        elif day == "R":
            result.append("Thursday")
        elif day == "F":
            result.append("Friday")
        elif day == "S":
            result.append("Saturday")
        elif day == "U":
            result.append("Sunday")
    return result

def get_time(time_str):
    if time_str:
        time_str = time_str.replace(":", "")
        if len(time_str) == 4:
            return datetime.time(int(time_str[:2]), int(time_str[2:]))
        elif len(time_str) == 3:
            return datetime.time(int(time_str[:1]), int(time_str[1:]))
        elif len(time_str) == 2:
            return datetime.time(int(time_str[:1]), 0)
    return None

def get_start_end_date(semester):
    year = int(semester.split(" ")[-1].split("-")[0]) + 1
    if semester.startswith("Fall"):
        year-=1
        start_date = datetime.date(int(year), 8, 1)
        end_date = datetime.date(int(year), 12, 31)
    elif semester.startswith("Spring"):
        start_date = datetime.date(int(year), 1, 1)
        end_date = datetime.date(int(year), 5, 31)
    elif semester.startswith("Summer"):
        start_date = datetime.date(int(year), 6, 1)
        end_date = datetime.date(int(year), 8, 31)
    else:
        raise HTTPException(status_code=400, detail="Invalid semester format")
    return start_date, end_date
        

@router.get("")
async def get_courses(
    semester: Optional[str] = 'Summer 2024-2025',
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get all courses filtered by semester.
    If no semester is provided, returns all courses.
    """
    query = db.query(Course)
    
    if semester:
        query = query.filter(Course.semester.like(f"%{semester}%"))
    
    courses = query.all()
    logging.info(f"Retrieved courses with semester filter: {semester}")
    return courses


@router.post("/register")
async def register_course(
    registration: CourseRegistration,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Register a student for a course"""
    # Check if course exists
    course = db.query(Course).filter(Course.course_id == registration.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if student is already registered for the course
    existing_registration = db.query(StudentCourse).filter(
        StudentCourse.student_id == current_student.student_id,
        StudentCourse.course_id == registration.course_id
    ).first()
    
    if existing_registration:
        raise HTTPException(status_code=400, detail="Student already registered for this course")
    
    # Create new registration
    new_registration = StudentCourse(
        student_id=current_student.student_id,
        course_id=registration.course_id
    )
    
    db.add(new_registration)
    db.commit()
    
    try:
        recurrences = course.timetable.get("times", [])
        for recurrence in recurrences:
            start_time = get_time(recurrence["start_time"])
            end_time = get_time(recurrence["end_time"])
            start_date, end_date = get_start_end_date(course.semester)
            if not start_time or not end_time:
                return {"message": "Invalid time format"}
            
            # Process each day string correctly
            # For example, "MWF" should be processed as individual chars
            days_string = recurrence.get("days", "")
            
            # Fix for course days processing - handle each character individually
            days_of_week = []
            for char in days_string:
                if char == 'M':
                    days_of_week.append("Monday")
                elif char == 'T':
                    days_of_week.append("Tuesday")
                elif char == 'W':
                    days_of_week.append("Wednesday")
                elif char == 'R':
                    days_of_week.append("Thursday")
                elif char == 'F':
                    days_of_week.append("Friday")
                elif char == 'S':
                    days_of_week.append("Saturday")
                elif char == 'U':
                    days_of_week.append("Sunday")
            
            # Fix: Properly await the coroutine
            await create_fixed_obligation(
                FixedObligationCreate(
                    name=course.course_name,
                    description=course.course_code + " Lecture", 
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=days_of_week,
                    start_date=start_date,
                    end_date=end_date,
                    recurrence="weekly",
                    priority=3,
                ),
                current_student=current_student,
                db=db,
            )
            
        # Call update_schedule to optimize the calendar
        # Temporarily disabled
        # updated_events = update_schedule({"student_id": current_student.student_id}, db)
        
        # If the course has a start date in the future, include it
        start_date, end_date = get_start_end_date(course.semester)
        
        # Pass the start_date to ensure the optimizer respects it
        optimization_payload = {
            "student_id": current_student.student_id
        }
        
        # If a future start date is specified, include it in the payload
        if start_date and start_date > datetime.datetime.now():
            optimization_payload["week_start"] = start_date
            
        updated_events = update_schedule(optimization_payload, db)
        return {"message": "Course registered successfully", "updated_events": updated_events}
    except Exception as e:
        logging.error(f"Error creating fixed obligation: {e}")
        raise HTTPException(status_code=500, detail="Error creating fixed obligation")

@router.get("/registered")
async def get_registered_courses(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get all courses registered by the student"""
    registered_courses = db.query(Course).\
        join(StudentCourse, StudentCourse.course_id == Course.course_id).\
        filter(StudentCourse.student_id == current_student.student_id).\
        all()
    
    # Convert courses to dictionaries manually
    courses_list = []
    for course in registered_courses:
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
    
    return {"courses": courses_list}

@router.delete("/unregister")
async def unregister_course(
    course_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Unregister a student from a course"""
    # Check if registration exists
    registration = db.query(StudentCourse).filter(
        StudentCourse.student_id == current_student.student_id,
        StudentCourse.course_id == course_id
    ).first()
    
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    db.delete(registration)
    db.commit()
    
    return {"message": "Course unregistered successfully"}
