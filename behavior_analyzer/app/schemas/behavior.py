from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any 
from datetime import datetime, time 

class SessionEventCreate(BaseModel):
    student_id: int 
    task_id: Optional[int] = None 
    start_time: datetime 
    estimated_duration: int = Field(..., description="Estimated duration in minutes")

class SessionEventUpdate(BaseModel):
    end_time: datetime 
    completed: bool
    self_rating: Optional[int] = Field(None, ge=1, le=5, description="Self-rating from 1 to 5")
    difficulty: Optional[int] = Field(None, ge=1, le=5, description="Difficulty from 1 to 5")
    notes: Optional[str] = None 

class ContextSignalCreate(BaseModel):
    student_id: int 
    event_type: str # class, meeting, exam 
    signal_type: str # sleep, exercise, commute 
    start_time: datetime 
    end_time: datetime 
    signal_value: Optional[Dict[str, Any]] = None 

class TimeSlot(BaseModel):
    day: str # Monday, Tuesday, etc...
    start_time: time 
    end_time: time 
    efficiency: float = Field(..., ge=0, le=1, description="Efficiency coefficient from 0 to 1")

class PeakWindow(BaseModel):
    day: str 
    start_time: time 
    end_time: time 
    efficiency: float 

# Update this class:
class ProductivityProfileResponse(BaseModel):
    student_id: int 
    slot_weights: Dict[str, float]
    peak_windows: List[PeakWindow]
    max_continuous_minutes: int 
    ideal_break_minutes: int 
    efficiency_decay_rate: float 
    fatigue_factor: float 
    recovery_factor: float 
    day_multipliers: Dict[str, float]
    soft_obligation_buffer: int 
    retention_rates: Optional[Dict[str, float]] = None 
    last_updated: datetime

    class Config:
        from_attributes = True 

class RecommendationRequest(BaseModel):
    student_id: int 
    task_duration: int
    task_type: Optional[str] = None