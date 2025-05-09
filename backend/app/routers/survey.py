from fastapi import APIRouter, Depends, HTTPException # type: ignore
from sqlalchemy.orm import Session
import logging
from app.database import get_db
from app.models.student import Student
from app.schemas.survey import SurveyAnswers
from app.models.course import Course
from app.auth.token import get_current_student


router = APIRouter(prefix="", tags=["survey"])

@router.get("/survey-questions")
async def get_survey_questions():
    sample_questions = [
        {
            "id": 1,
            "question": "What time do you prefer to study?",
            "type": "mcq",
            "options": ["Morning", "Afternoon", "Evening", "Late night"],
        },
        {
            "id": 2,
            "question": "What time do you usually wake up?",
            "type": "time",
        },
        {
            "id": 3,
            "question": "How long can you study before needing a break?",
            "type": "mcq",
            "options": ["30 minutes", "1 hour", "2 hours", "More than 2 hours"],
        },
        {
            "id": 4,
            "question": "What's your preferred study environment?",
            "type": "mcq",
            "options": ["Library", "Coffee shop", "Home", "Outdoors"],
        },
        {
            "id": 5,
            "question": "Do you have any specific times you're unavailable to study?",
            "type": "text",
        },
    ]
    return sample_questions

@router.post("/survey-answers")
async def submit_survey_answers(
    answers: SurveyAnswers,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Save the survey answers to the database.
    """

    # Check if the student is already registered
    student = db.query(Student).filter(Student.student_id == current_student.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    # Save the survey answers to the database
    logging.info(f"answers: {answers}")
    student.preferences = answers.dict()
    db.commit()
    db.refresh(student)
    logging.info(f"Survey answers saved for student ID: {student.student_id}")
    return {"message": "Survey answers saved successfully"}