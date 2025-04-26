from sqlalchemy import Column, String, Integer, TIMESTAMP, JSON, text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Course(Base):
    __tablename__ = "courses"
    
    course_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_code = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    course_CRN = Column(Integer, unique=True, nullable=False)
    course_section = Column(Integer, nullable=False)
    course_credits = Column(Integer, nullable=False)
    actual_enrollment = Column(Integer, nullable=False)
    max_enrollment = Column(Integer, nullable=False)
    instructor = Column(String)
    semester = Column(String, nullable=False)
    timetable = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class StudentCourse(Base):
    __tablename__ = "student_courses"
    
    student_course_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    registered_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))