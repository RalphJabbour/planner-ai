from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean, Float, ForeignKey, text
from app.database import Base
from datetime import datetime

class SessionLog(Base):
    __tablename__ = "session_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    pages_read = Column(Integer, nullable=False)
    focus_rating = Column(Integer, nullable=False)
    completed = Column(Boolean, nullable=False)
    device = Column(String)
    timezone = Column(String)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class FeatureAggregate(Base):
    __tablename__ = "feature_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"))
    date = Column(TIMESTAMP, nullable=False)
    avg_duration_7d = Column(Float)
    avg_efficiency_7d = Column(Float)
    completion_rate_7d = Column(Float)
    avg_duration_30d = Column(Float)
    avg_efficiency_30d = Column(Float)
    completion_rate_30d = Column(Float)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class ModelPerformance(Base):
    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    training_date = Column(TIMESTAMP, nullable=False)
    mse = Column(Float)
    mae = Column(Float)
    r2 = Column(Float)
    auc = Column(Float)
    f1_score = Column(Float)
    accuracy = Column(Float)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

