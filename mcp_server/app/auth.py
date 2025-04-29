from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.reflected_models import Student
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - reuse the same keys from the main backend
SECRET_KEY = os.getenv('SECRET_KEY', "your-secret-key-should-be-very-long-and-secure")
ALGORITHM = os.getenv('ALGORITHM', "HS256")

def validate_token(token: Optional[str], db: Session) -> Optional[Student]:
    """
    Validate JWT token
    Returns the authenticated student or None
    """
    if not token:
        return None
    
    try:
        # Parse the token to extract Bearer token if provided with "Bearer " prefix
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        # Decode and validate the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        if student_id is None:
            return None
            
        # Get the student from the database
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if student is None:
            return None
            
        return student
    except JWTError:
        return None

def get_current_student_from_token(token: Optional[str], db: Session) -> Student:
    """
    Get current student from token or raise exception
    """
    student = validate_token(token, db)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return student
