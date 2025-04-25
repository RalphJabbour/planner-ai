from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any 
from datetime import datetime, time, timezone

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
        orm_mode = True 

class RecommendationRequest(BaseModel):
    student_id: int 
    task_duration: int
    task_type: Optional[str] = None

# New schemas for passing data via request
class SessionEventData(BaseModel):
    event_id: int
    student_id: int
    task_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    completed: bool = False
    self_rating: Optional[int] = None
    difficulty: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

class ContextSignalData(BaseModel):
    signal_id: int
    student_id: int
    event_type: str
    start_time: datetime
    end_time: datetime
    signal_type: str
    signal_value: Optional[Dict[str, Any]] = None
    created_at: datetime

class ProductivityProfileData(BaseModel):
    profile_id: int
    student_id: int
    slot_weights: Dict[str, float]
    peak_windows: List[Dict[str, Any]]
    max_continuous_minutes: int
    ideal_break_minutes: int
    efficiency_decay_rate: float
    fatigue_factor: float
    recovery_factor: float
    day_multipliers: Dict[str, float]
    soft_obligation_buffer: float
    retention_rates: Optional[Dict[str, float]] = None
    last_updated: datetime

class DataPackageRequest(BaseModel):
    sessions: List[SessionEventData] = []
    context_signals: List[ContextSignalData] = []
    profile: Optional[ProductivityProfileData] = None
    
    @classmethod
    def get_sample(cls, student_id: int = 1) -> 'DataPackageRequest':
        """
        Creates a sample data package for testing
        """
        # Create sample sessions
        sessions = [
            SessionEventData(
                event_id=101,
                student_id=student_id,
                task_id=201,
                start_time=datetime(2023, 4, 15, 9, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2023, 4, 15, 10, 30, 0, tzinfo=timezone.utc),
                estimated_duration=60,
                actual_duration=90,
                completed=True,
                self_rating=4,
                difficulty=3,
                notes="Felt productive but took longer than expected",
                created_at=datetime(2023, 4, 15, 8, 55, 0, tzinfo=timezone.utc)
            ),
            SessionEventData(
                event_id=102,
                student_id=student_id,
                task_id=202,
                start_time=datetime(2023, 4, 16, 14, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2023, 4, 16, 15, 0, 0, tzinfo=timezone.utc),
                estimated_duration=60,
                actual_duration=60,
                completed=True,
                self_rating=5,
                difficulty=2,
                notes="Great focus today",
                created_at=datetime(2023, 4, 16, 13, 55, 0, tzinfo=timezone.utc)
            )
        ]
        
        # Create sample context signals
        context_signals = [
            ContextSignalData(
                signal_id=501,
                student_id=student_id,
                event_type="class",
                signal_type="academic",
                start_time=datetime(2023, 4, 15, 13, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2023, 4, 15, 14, 30, 0, tzinfo=timezone.utc),
                signal_value={"class_name": "CS 303"},
                created_at=datetime(2023, 4, 15, 8, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        # Create sample profile
        profile = ProductivityProfileData(
            profile_id=1,
            student_id=student_id,
            slot_weights={
                "Monday-9": 0.82,
                "Monday-10": 0.85,
                "Monday-14": 0.65
            },
            peak_windows=[],
            max_continuous_minutes=45,
            ideal_break_minutes=10,
            efficiency_decay_rate=0.05,
            fatigue_factor=0.15,
            recovery_factor=0.2,
            day_multipliers={
                "Monday": 1.0,
                "Tuesday": 1.1,
                "Wednesday": 0.9,
                "Thursday": 1.0,
                "Friday": 0.8,
                "Saturday": 1.2,
                "Sunday": 1.0
            },
            soft_obligation_buffer=30,
            retention_rates={},
            last_updated=datetime(2023, 4, 18, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        return cls(
            sessions=sessions,
            context_signals=context_signals,
            profile=profile
        )

# Updated request classes
class ProfileUpdateRequest(BaseModel):
    student_id: int
    data_package: DataPackageRequest
    force_update: bool = False

class GetProfileRequest(BaseModel):
    student_id: int
    data_package: DataPackageRequest

class SessionSuccessPredictionRequest(BaseModel):
    student_id: int
    start_time: datetime
    duration: int
    data_package: DataPackageRequest

class RecommendationRequestWithData(BaseModel):
    student_id: int 
    task_duration: int
    task_type: Optional[str] = None
    data_package: DataPackageRequest

class ColdStartRequest(BaseModel):
    student_id: int
    preferences: Optional[Dict[str, Any]] = None
    data_package: DataPackageRequest