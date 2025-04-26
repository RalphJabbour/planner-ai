from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class AcademicTask(Base):
    #for each chapter of a course there should be a task for it
    #for each assignment and for each exam there should be a task
    __tablename__ = "academic_tasks"
    
    task_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))

    task_type = Column(String(50))
    title = Column(String, nullable=False)
    description = Column(Text)
    deadline = Column(TIMESTAMP, nullable=False)

    status = Column(String(50), default="pending")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint(task_type.in_(['revision', 'assignment', 'project', 'exam'])),
        CheckConstraint(status.in_(['pending', 'in_progress', 'completed', 'overdue'])),
    )
    #eventually when the application gets bigger, we will have to add subtasks (which may be created by LLMs + RAG):
    #for example, if the task is exam, the subtasks may be:
    #1. revision
    #2. practice exam
    #3. review exam
    #4. exam day
    #5. exam feedback

class StudyMaterial(Base):
    # will be used to create academic tasks
    __tablename__ = "study_materials"
    
    material_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
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
