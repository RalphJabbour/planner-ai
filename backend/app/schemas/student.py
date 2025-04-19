from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class StudentBase(BaseModel):
    name: str
    email: str  # Consider using EmailStr if email-validator is installed

class StudentCreate(StudentBase):
    password: str
    program: Optional[str] = None
    year: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None

class StudentResponse(StudentBase):
    student_id: int
    program: Optional[str] = None
    year: Optional[int] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class StudentLogin(BaseModel):
    email: str
    password: str