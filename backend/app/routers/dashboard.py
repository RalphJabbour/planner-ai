from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.models.academic import AcademicTask
from app.models.schedule import CalendarEvent
from app.auth.token import get_current_student
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/")
async def get_dashboard(
    current_student: Student = Depends(get_current_student), 
    db: Session = Depends(get_db)
):
    """
    Get dashboard information for the logged-in student
    Includes:
    - Student profile
    - Registered courses
    - Upcoming tasks
    - Recent activity
    """
    # Get student's courses
    courses = db.query(Course).\
        join(StudentCourse, StudentCourse.course_id == Course.course_id).\
        filter(StudentCourse.student_id == current_student.student_id).\
        all()
    
    # Get upcoming tasks (next 7 days)
    today = datetime.now()
    next_week = today + timedelta(days=7)
    upcoming_tasks = db.query(AcademicTask).\
        join(StudentCourse, StudentCourse.course_id == AcademicTask.course_id).\
        filter(StudentCourse.student_id == current_student.student_id).\
        filter(AcademicTask.deadline >= today).\
        filter(AcademicTask.deadline <= next_week).\
        order_by(AcademicTask.deadline).\
        all()
    
    # Get upcoming calendar events
    upcoming_events = db.query(CalendarEvent).\
        filter(CalendarEvent.student_id == current_student.student_id).\
        filter(CalendarEvent.start_time >= today).\
        filter(CalendarEvent.start_time <= next_week).\
        order_by(CalendarEvent.start_time).\
        all()
    
    # Format the response
    return {
        "student": {
            "id": current_student.student_id,
            "name": current_student.name,
            "email": current_student.email,
            "program": current_student.program,
            "year": current_student.year,
        },
        "courses": [
            {
                "id": course.course_id,
                "code": course.course_code,
                "name": course.course_name,
                "instructor": course.instructor,
                "semester": course.semester
            } for course in courses
        ],
        "upcoming_tasks": [
            {
                "id": task.task_id,
                "title": task.title,
                "type": task.task_type,
                "deadline": task.deadline,
                "course_id": task.course_id,
                "status": task.status
            } for task in upcoming_tasks
        ],
        "upcoming_events": [
            {
                "id": event.event_id,
                "type": event.event_type,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "priority": event.priority,
                "status": event.status
            } for event in upcoming_events
        ],
        "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }