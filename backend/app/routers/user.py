import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.auth.token import get_current_student

router = APIRouter(prefix="/users", tags=["users"])  # Fixed tag to "users" instead of "courses"


@router.get("/me")
async def get_user_info(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get user information.
    """
    user_info = {
        "student_id": current_student.student_id,
        "name": current_student.name,
        "email": current_student.email,
        "program": current_student.program,
        "year": current_student.year,
        "preferences": current_student.preferences,
    }
    
    logging.info(f"User info retrieved for: {current_student.email}")
    return user_info

