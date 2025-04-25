from app.routers import tasks
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import app.models
from app.database import engine, Base, get_db
from app.routers import auth, survey, courses, ai_assistant, user, tasks
# from app.routers import chat
import logging
import os
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.routers.auth import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Planner API")

# CORS middleware
origins = [
    "http://localhost:5173",  # React development server default port
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(survey.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(user.router, prefix="/api")

# app.include_router(chat.router, prefix="/api")

# app.include_router(ai_assistant.router, prefix="/api")

# API Key security setup for the initialization endpoint
API_KEY = os.getenv("INIT_API_KEY", "course-sync-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

@app.get("/")
async def root():
    return {"message": "Welcome to the Student Planner API"}

# Function to initialize default user and courses
async def initialize_default_data(db: Session):
    try:
        # Check if default user exists
        default_email = "demo@example.com"
        existing_user = db.query(Student).filter(Student.email == default_email).first()
        
        if not existing_user:
            # Create default user
            logger.info("Creating default demo user...")
            hashed_password = hash_password("demopassword")
            
            default_user = Student(
                name="Demo Student",
                email=default_email,
                password_hash=hashed_password,
                program="CSE",
                year=3,
                preferences={"study_preference": "morning", "campus_time": "afternoon"}
            )
            
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            user_id = default_user.student_id
            logger.info(f"Created default user with ID: {user_id}")
        else:
            user_id = existing_user.student_id
            logger.info(f"Default user already exists with ID: {user_id}")
        
        # Check if the user already has courses
        existing_courses = db.query(StudentCourse).filter(StudentCourse.student_id == user_id).count()
        
        crns_to_register = [30318, 30363, 30317]
        if existing_courses == 0:
            # Get some courses to register for the user
            courses = db.query(Course).filter(Course.course_CRN.in_(crns_to_register)).all()
            
            if courses:
                # Register user for these courses
                for course in courses:
                    student_course = StudentCourse(
                        student_id=user_id,
                        course_id=course.course_id
                    )
                    db.add(student_course)
                
                db.commit()
                logger.info(f"Registered default user for {len(courses)} courses")
                return {"success": True, "user_id": user_id, "courses_registered": len(courses)}
            else:
                logger.warning(f"No courses found with the specified CRNs: {crns_to_register}")
                return {"success": True, "user_id": user_id, "courses_registered": 0, "warning": "No courses found with the specified CRNs"}
        else:
            logger.info(f"User already has {existing_courses} courses registered")
            return {"success": True, "user_id": user_id, "courses_already_registered": existing_courses}
    
    except Exception as e:
        logger.error(f"Error initializing default data: {str(e)}")
        db.rollback()
        return {"success": False, "error": str(e)}

# Endpoint that course-sync service can call after populating the course table
@app.post("/api/admin/initialize-default-data")
async def initialize_default_data_endpoint(api_key: str = Security(verify_api_key), db: Session = Depends(get_db)):
    """
    Initialize the default user and register them for courses.
    This endpoint should be called after course data has been synced to the database.
    """
    result = await initialize_default_data(db)
    return result