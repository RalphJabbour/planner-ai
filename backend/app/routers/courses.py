import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.auth.token import get_current_student

router = APIRouter(prefix="/courses", tags=["courses"])

class CourseRegistration(BaseModel):
    course_id: int

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
    
    return {"message": "Course registered successfully"}

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
