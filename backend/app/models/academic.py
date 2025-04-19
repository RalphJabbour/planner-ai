from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class AcademicTask(Base):
    __tablename__ = "academic_tasks"
    
    task_id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    task_type = Column(String(50))
    title = Column(String, nullable=False)
    description = Column(Text)
    deadline = Column(TIMESTAMP, nullable=False)
    estimated_hours = Column(NUMERIC)
    status = Column(String(50), default="pending")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint(task_type.in_(['assignment', 'project', 'exam'])),
    )

class StudyMaterial(Base):
    __tablename__ = "study_materials"
    
    material_id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="SET NULL"))
    material_type = Column(String(50))
    title = Column(String)
    url = Column(Text)
    chapter = Column(String(100))
    expected_time = Column(NUMERIC)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint(material_type.in_(['pdf', 'powerpoint', 'testbank', 'book_exercise'])),
    )

class CourseProgress(Base):
    __tablename__ = "course_progress"
    
    progress_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"))
    task_type = Column(String(50))
    chapter = Column(String(100))
    percentage_completed = Column(NUMERIC)
    hours_spent = Column(NUMERIC)
    proficiency_score = Column(NUMERIC)
    last_updated = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(task_type.in_(['chapter_study', 'project', 'problem_solving'])),
    )