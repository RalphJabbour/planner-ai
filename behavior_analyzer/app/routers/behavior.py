from fastapi import APIRouter, HTTPException, status, Depends
from app.database import get_db
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from app.schemas.behavior import (
    SessionEventCreate, SessionEventUpdate, ContextSignalCreate,
    ProductivityProfileResponse, TimeSlot,
    DataPackageRequest, ProfileUpdateRequest, GetProfileRequest,
    SessionSuccessPredictionRequest, ColdStartRequest,
    RecommendationRequestWithData, RecommendationRequest
)
from app.models.reflected_models import SessionEvent, ContextSignal, ProductivityProfile
from app.ml.models import BehaviorModel

router = APIRouter(prefix="/behavior", tags=["behavior"])

# Session events endpoints
@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_session(session: SessionEventCreate, db: Session = Depends(get_db)):
    """
    Create a new session event (start of a study session)
    """
    new_session = SessionEvent(
        student_id=session.student_id,
        task_id=session.task_id,
        start_time=session.start_time,
        estimated_duration=session.estimated_duration
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {"event_id": new_session.event_id, "message": "Session started successfully"}

@router.put("/session/{event_id}")
async def update_session(event_id: int, update: SessionEventUpdate, db: Session = Depends(get_db)):
    """
    Update a session event (complete a session with feedback)
    """
    session = db.query(SessionEvent).filter(SessionEvent.event_id == event_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update fields
    session.end_time = update.end_time
    session.completed = update.completed
    session.self_rating = update.self_rating
    session.difficulty = update.difficulty
    session.notes = update.notes
    
    # Calculate actual duration in minutes
    if session.start_time and update.end_time:
        # Convert end_time to naive datetime if start_time is naive
        end_time_naive = update.end_time.replace(tzinfo=None)
        delta = end_time_naive - session.start_time
        session.actual_duration = delta.total_seconds() / 60
    
    db.commit()
    db.refresh(session)
    
    # Update productivity profile after session feedback
    model = BehaviorModel(db)
    model.update_profile(session.student_id)
    
    return {"message": "Session updated successfully"}

# Context signals endpoints
@router.post("/context", status_code=status.HTTP_201_CREATED)
async def create_context_signal(signal: ContextSignalCreate, db: Session = Depends(get_db)):
    """
    Log a context signal (calendar event, sleep, exercise, etc.)
    """
    new_signal = ContextSignal(
        student_id=signal.student_id,
        event_type=signal.event_type,
        signal_type=signal.signal_type,
        start_time=signal.start_time,
        end_time=signal.end_time,
        signal_value=signal.signal_value
    )
    
    db.add(new_signal)
    db.commit()
    db.refresh(new_signal)
    
    return {"signal_id": new_signal.signal_id, "message": "Context signal logged successfully"}

@router.get("/profile/{student_id}", response_model=ProductivityProfileResponse)
async def get_productivity_profile(student_id: int, db: Session = Depends(get_db)):
    """
    Get the current productivity profile for a student
    """
    model = BehaviorModel(db)
    profile = model.get_or_create_profile(student_id)
    
    return profile

@router.post("/profile/{student_id}/update")
async def update_productivity_profile(student_id: int, db: Session = Depends(get_db)):
    """
    Force an update of the productivity profile
    """
    model = BehaviorModel(db)
    profile = model.update_profile(student_id, force_update=True)
    
    return {"message": "Profile updated successfully"}

@router.post("/recommendation", response_model=List[Dict])
async def get_recommendations(request: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Get recommended time slots for a task
    """
    model = BehaviorModel(db)
    recommendations = model.recommend_slots(
        student_id=request.student_id,
        task_duration=request.task_duration
    )
    
    return recommendations

@router.post("/profile/{student_id}/cold-start")
async def initialize_profile(student_id: int, preferences: Optional[Dict] = None, db: Session = Depends(get_db)):
    """
    Initialize a profile for a new student
    """
    model = BehaviorModel(db)
    profile = model.initialize_cold_start(student_id, preferences)
    
    return {"message": "Profile initialized successfully"}

@router.post("/predict/session")
async def predict_session_success(
    student_id: int, 
    start_time: datetime, 
    duration: int, 
    db: Session = Depends(get_db)
):
    """
    Predict success probability and efficiency for a potential session
    """
    model = BehaviorModel(db)
    prediction = model.predict_session_success(
        student_id=student_id,
        start_time=pd.Timestamp(start_time),
        duration=duration
    )
    
    return prediction

@router.get("/api/behavior/scheduling-parameters/{student_id}")
async def get_scheduling_parameters(student_id: int, db: Session = Depends(get_db)):
    """
    Returns all parameters needed by OR-Tools scheduler
    """
    model = BehaviorModel(db)
    profile = model.get_or_create_profile(student_id)
    
    # Structure for OR-Tools integration
    return {
        "slot_efficiencies": profile.slot_weights,
        "session_constraints": {
            "max_continuous_minutes": profile.max_continuous_minutes,
            "ideal_break_minutes": profile.ideal_break_minutes,
            "min_session_length": 20,  # Minimum viable session
            "efficiency_decay_rate": profile.efficiency_decay_rate
        },
        "fatigue_model": {
            "fatigue_factor": profile.fatigue_factor,
            "recovery_factor": profile.recovery_factor,
            "daily_energy_budget": 360  # 6 productive hours per day
        },
        "calendar_constraints": {
            "buffer_minutes": profile.soft_obligation_buffer,
            "transition_penalty": 0.1,  # 10% efficiency loss on subject transitions
        },
        "day_multipliers": profile.day_multipliers,
        "peak_windows": profile.peak_windows
    }