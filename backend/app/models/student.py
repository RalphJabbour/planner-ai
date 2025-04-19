from sqlalchemy import Column, String, Integer, TIMESTAMP, JSON, text
from app.database import Base

class Student(Base):
    __tablename__ = "students"
    
    student_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String)
    program = Column(String)
    year = Column(Integer)
    preferences = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))