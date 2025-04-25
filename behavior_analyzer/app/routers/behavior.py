from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from app.schemas.behavior import (
    SessionEventCreate, SessionEventUpdate, ContextSignalCreate,
    ProductivityProfileResponse, TimeSlot,
    DataPackageRequest, ProfileUpdateRequest, GetProfileRequest,
    SessionSuccessPredictionRequest, ColdStartRequest,
    RecommendationRequestWithData
)
from app.ml.models import BehaviorModel

router = APIRouter(prefix="/behavior", tags=["behavior"])

# Session events endpoints
@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_session(session: SessionEventCreate):
    """
    Create a new session event (start of a study session)
    """
    # Now just return a placeholder response - actual DB integration will be handled in business logic
    return {"event_id": 0, "message": "Session started successfully"}

@router.put("/session/{event_id}")
async def update_session(event_id: int, update: SessionEventUpdate):
    """
    Update a session event (complete a session with feedback)
    """
    # Now just return a placeholder response - actual DB integration will be handled in business logic
    return {"message": "Session updated successfully"}

# Context signals endpoints
@router.post("/context", status_code=status.HTTP_201_CREATED)
async def create_context_signal(signal: ContextSignalCreate):
    """
    Log a context signal (calendar event, sleep, exercise, etc.)
    """
    # Now just return a placeholder response - actual DB integration will be handled in business logic
    return {"signal_id": 0, "message": "Context signal logged successfully"}

@router.post("/profile/{student_id}", response_model=ProductivityProfileResponse)
async def get_productivity_profile(request: GetProfileRequest):
    """
    Get the current productivity profile for a student
    """
    model = BehaviorModel(request.data_package)
    profile = model.get_or_create_profile(request.student_id)
    
    return profile

@router.post("/profile/{student_id}/update")
async def update_productivity_profile(request: ProfileUpdateRequest):
    """
    Force an update of the productivity profile
    """
    model = BehaviorModel(request.data_package)
    profile = model.update_profile(request.student_id, force_update=request.force_update)
    
    return {"message": "Profile updated successfully", "profile": profile}

@router.post("/recommendation", response_model=List[Dict])
async def get_recommendations(request: RecommendationRequestWithData):
    """
    Get recommended time slots for a task
    """
    model = BehaviorModel(request.data_package)
    recommendations = model.recommend_slots(
        student_id=request.student_id,
        task_duration=request.task_duration
    )
    
    return recommendations

@router.post("/profile/{student_id}/cold-start")
async def initialize_profile(request: ColdStartRequest):
    """
    Initialize a profile for a new student
    """
    model = BehaviorModel(request.data_package)
    profile = model.initialize_cold_start(request.student_id, request.preferences)
    
    return {"message": "Profile initialized successfully", "profile": profile}

@router.post("/predict/session")
async def predict_session_success(request: SessionSuccessPredictionRequest):
    """
    Predict success probability and efficiency for a potential session
    """
    model = BehaviorModel(request.data_package)
    prediction = model.predict_session_success(
        student_id=request.student_id,
        start_time=pd.Timestamp(request.start_time),
        duration=request.duration
    )
    
    return prediction

@router.post("/scheduling-parameters/{student_id}")
async def get_scheduling_parameters(student_id: int, data_package: DataPackageRequest):
    """
    Returns all parameters needed by OR-Tools scheduler
    """
    model = BehaviorModel(data_package)
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