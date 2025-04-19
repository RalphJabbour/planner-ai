from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import timedelta
from app.database import get_db
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentLogin
from app.auth.token import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/signup")
async def signup(student: StudentCreate, db: Session = Depends(get_db)):
    # Check if student already exists
    db_student = db.query(Student).filter(Student.email == student.email).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new student with hashed password
    hashed_password = hash_password(student.password)
    db_student = Student(
        name=student.name,
        email=student.email,
        password_hash=hashed_password,
        program=student.program,
        year=student.year,
        preferences=student.preferences
    )
    
    # Add to database
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_student.student_id)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "message": "Signup successful.",
        "student_id": db_student.student_id, 
        "student_name": db_student.name,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/login")
async def login(student_data: StudentLogin, db: Session = Depends(get_db)):
    # Find student by email
    db_student = db.query(Student).filter(Student.email == student_data.email).first()
    
    # Verify student exists and password is correct
    if not db_student or not verify_password(student_data.password, db_student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_student.student_id)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "message": "Login successful.",
        "student_id": db_student.student_id, 
        "student_name": db_student.name,
        "access_token": access_token,
        "token_type": "bearer"
    }