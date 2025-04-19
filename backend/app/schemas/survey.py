from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SurveyQuestion(BaseModel):
    id: int
    question: str
    type: str
    options: Optional[List[str]] = None

class SurveyAnswers(BaseModel):
    student_id: int
    answers: Dict[str, Any]