from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, Time, ForeignKey, CheckConstraint, Boolean, JSON, ARRAY, DATE, TIME
from sqlalchemy.sql import text
from app.database import Base
import datetime

class FixedObligation(Base):
    __tablename__ = "fixed_obligations"

    obligation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    start_time = Column(TIME, nullable=False)
    end_time = Column(TIME, nullable=False)
    days_of_week = Column(ARRAY(String), nullable=False)
    start_date = Column(DATE, nullable=False)
    end_date = Column(DATE, nullable=True)
    recurrence = Column(String, nullable=True)

    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="cascade"), nullable=True)

    priority = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    def to_dict(self):
        return {
            "obligation_id": self.obligation_id,
            "student_id": self.student_id,
            "name": self.name,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "days_of_week": self.days_of_week,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "recurrence": self.recurrence,
            "course_id": self.course_id,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class FlexibleObligation(Base):
    __tablename__ = "flexible_obligations"
    
    obligation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    weekly_target_hours = Column(NUMERIC, nullable=False)
    constraints = Column(JSON)
    start_date = Column(TIMESTAMP)
    end_date = Column(TIMESTAMP)
    priority = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    def to_dict(self):
        return {
            "obligation_id": self.obligation_id,
            "student_id": self.student_id,
            "description": self.description,
            "weekly_target_hours": float(self.weekly_target_hours),
            "constraints": self.constraints,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# TODO: we still have not used this table
class PersonalizedStudySession(Base):
    __tablename__ = "study_sessions"
    
    session_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"))
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"))
    description = Column(Text, nullable=False)
    estimated_hours = Column(NUMERIC)  # To be predicted by AI
    preferred_chunk_size = Column(NUMERIC)  # To be predicted by AI
    priority = Column(Integer, default=3)  # To be predicted by AI
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)
    actual_hours = Column(NUMERIC)
    feedback = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "task_id": self.task_id,
            "course_id": self.course_id,
            "description": self.description,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None,
            "preferred_chunk_size": float(self.preferred_chunk_size) if self.preferred_chunk_size else None,
            "priority": self.priority,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "actual_hours": float(self.actual_hours) if self.actual_hours else None,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

#TODO: we still have not used this table
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
    
    event_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    
    event_type = Column(String(50)) # either 'fixed_obligation', 'flexible_obligation', 'study_session', or 'course_lecture'
    fixed_obligation_id = Column(Integer, ForeignKey("fixed_obligations.obligation_id", ondelete="SET NULL"), nullable=True)
    flexible_obligation_id = Column(Integer, ForeignKey("flexible_obligations.obligation_id", ondelete="SET NULL"), nullable=True)
    study_session_id = Column(Integer, ForeignKey("study_sessions.session_id", ondelete="SET NULL"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)
    
    date = Column(TIMESTAMP, nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)

    priority = Column(Integer)
    status = Column(String(50), default="scheduled")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        CheckConstraint("event_type IN ('course_lecture', 'study_session', 'fixed_obligation', 'flexible_obligation')"),
        CheckConstraint('priority BETWEEN 1 AND 5'),
    )

#TODO: we still have not used this table
class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    event_id = Column(Integer, ForeignKey("calendar_events.event_id", ondelete="SET NULL"))
    notification_time = Column(TIMESTAMP, nullable=False)
    message = Column(Text)
    delivered = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))