from sqlalchemy import Column, String, Integer, TIMESTAMP, NUMERIC, Text, ForeignKey, Boolean, Float, JSON
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from app.database import Base
import datetime 

class SessionEvent(Base):
    """
    Captures detailed study session event for behavior analysis
    """
    __tablename__ = "behavior_session_events"

    event_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("academic_tasks.task_id", ondelete="CASCADE"), nullable=True)
    #Session timing info
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=True) # Null until completed
    estimated_duration = Column(NUMERIC, nullable=True) # In minutes
    actual_duration = Column(NUMERIC, nullable=True) # In minutes, null until completed

    # Post-session feedback
    completed = Column(Boolean, default=False)
    self_rating = Column(Integer, nullable=True) # 1-5 scale
    difficulty = Column(Integer, nullable=True) # 1-5 scale
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class ContextSignal(Base):
    """
    Store context signals that may affect productivity
    """
    __tablename__ = "context_signals"

    signal_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))

    # Calendar event type (class, meeting, exam)
    event_type = Column(String(50), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)

    # Optional logs
    signal_type = Column(String(50), nullable=False) # sleep, exercise, commute, etc.
    signal_value = Column(JSON, nullable=True) # JSON for flexible logging

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class ProductivityProfile(Base):
    """
    Stores the computed productivity profile for each student
    """
    __tablename__ = "behavior_productivity_profiles"

    profile_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))

    # Slot efficiency data stored as JSON
    slot_weights = Column(JSON, nullable=False) # Map of time slots to efficiency coefficients
    peak_windows = Column(JSON, nullable=False) # List of high-efficiency time windows

    # Session parameters
    max_continuous_minutes = Column(Integer, nullable=False, default=45)
    ideal_break_minutes = Column(Integer, nullable=False, default=10)
    efficiency_decay_rate = Column(Float, nullable=False, default=0.05) # Per extra minute

    # Fatigue parameters
    fatigue_factor = Column(Float, nullable=False, default=0.15) # Reduction after back-to-back sessions
    recovery_factor = Column(Float, nullable=False, default=0.2) # Recovery after breaks

    # Adjustment factors
    day_multipliers = Column(JSON, nullable=False) # Map of days to multipliers
    soft_obligation_buffer = Column(Float, nullable=False, default=30) # In minutes

    # Optimal retention indicators
    retention_rates = Column(JSON, nullable=True) # Map of slots to retention rates

    last_updated = Column(TIMESTAMP, default=datetime.datetime.now(datetime.UTC))






