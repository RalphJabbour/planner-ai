from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, Time, ForeignKey, CheckConstraint, Boolean, JSON
from sqlalchemy.sql import text
from app.database import Base

class FixedObligation(Base):
    __tablename__ = "fixed_obligations"
    
    obligation_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    day_of_week = Column(String(20), nullable=False)
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
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class StudySession(Base):
    __tablename__ = "study_sessions"
    
    session_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    chapter = Column(String(100))
    start_chapter = Column(String(100))
    planned_chapters = Column(JSON, server_default='[]')
    actual_chapters = Column(JSON, server_default='[]')
    planned_start = Column(TIMESTAMP, nullable=False)
    planned_end = Column(TIMESTAMP, nullable=False)
    actual_start = Column(TIMESTAMP)
    actual_end = Column(TIMESTAMP)
    actual_hours = Column(NUMERIC)
    feedback = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    event_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    event_type = Column(String(50))
    reference_id = Column(Integer)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    priority = Column(Integer)
    status = Column(String(50), default="scheduled")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint(event_type.in_(['class', 'study_session', 'fixed_obligation', 'flexible_obligation'])),
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