from sqlalchemy import Column, String, Integer, TIMESTAMP, Date, Text, JSON, ForeignKey
from sqlalchemy.sql import text
from app.database import Base

# TODO: we still have not used this table
class DailyLog(Base):
    __tablename__ = "daily_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    log_date = Column(Date, nullable=False)
    planned_schedule = Column(JSON)
    completed_schedule = Column(JSON)
    progress_updates = Column(JSON)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))