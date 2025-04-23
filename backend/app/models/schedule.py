from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, Time, ForeignKey, CheckConstraint, Boolean, JSON
from sqlalchemy.sql import text
from app.database import Base
import datetime

class FixedObligation(Base):
    __tablename__ = "fixed_obligations"
    
    obligation_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    is_course_lecture = Column(Boolean, default=False)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=True)

    name = Column(String, nullable=False)
    description = Column(Text)
    
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    days_of_week = Column(JSON, server_default='[]') 

    start_date = Column(TIMESTAMP)
    end_date = Column(TIMESTAMP) 
    recurrence = Column(String(50))
    priority = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint('priority BETWEEN 1 AND 5'),
    )

class FlexibleObligation(Base):
    __tablename__ = "flexible_obligations"
    
    obligation_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))

    description = Column(Text, nullable=False)
    weekly_target_hours = Column(NUMERIC, nullable=False)
    constraints = Column(JSON)
    start_date = Column(TIMESTAMP)
    end_date = Column(TIMESTAMP)
    priority = Column(Integer)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class PersonalizedStudySession(Base): 
    #for each chapter of a course there should be a task for it
    #for each assignment and for each exam there should be a task
    #for each task, there should be a 
    __tablename__ = "study_sessions"
    
    session_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))

    description = Column(Text, nullable=False)

    estimated_hours = Column(NUMERIC) #!!!!! to be predicted by AI IEP - to be learnt from user behavior
    preferred_chunk_size = Column(NUMERIC) #!!!! to be predicted by AI IEP
    priority = Column(Integer, default=3)  # !!!! also to predicted by AI IEP

    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)

    #should feed back into the course progress of the academic task
    #this means 
    
    actual_hours = Column(NUMERIC)
    feedback = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class TaskProgress(Base): # will be used to be able to better predict the needed hours for an academic task for a specific student
    __tablename__ = "task_progress"
    
    progress_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))

    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"))
    flexible_obligation_id = Column(Integer, ForeignKey("flexible_obligations.obligation_id", ondelete="SET NULL"), nullable=True)

    hours_spent = Column(NUMERIC)
    percentage_completed = Column(NUMERIC)
    proficiency_score = Column(NUMERIC)

    last_updated = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    event_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    
    event_type = Column(String(50)) # either 'fixed_obligation', 'flexible_obligation', 'study_session', or 'class'
    fixed_obligation_id = Column(Integer, ForeignKey("fixed_obligations.obligation_id", ondelete="SET NULL"), nullable=True)
    flexible_obligation_id = Column(Integer, ForeignKey("flexible_obligations.obligation_id", ondelete="SET NULL"), nullable=True)
    study_session_id = Column(Integer, ForeignKey("study_sessions.session_id", ondelete="SET NULL"), nullable=True)
    
    date = Column(TIMESTAMP, nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)

    priority = Column(Integer)
    status = Column(String(50), default="scheduled")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint("event_type IN ('class', 'study_session', 'fixed_obligation', 'flexible_obligation')"),
        CheckConstraint('priority BETWEEN 1 AND 5'),
    )

class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    event_id = Column(Integer, ForeignKey("calendar_events.event_id", ondelete="SET NULL"))
    notification_time = Column(TIMESTAMP, nullable=False)
    message = Column(Text)
    delivered = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))