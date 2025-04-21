from fastapi import APIRouter, Depends, HTTPException 
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.behavior import SessionLog as SessionLogModel, FeatureAggregate
from app.ml.recommendation import get_recommendations
from app.monitoring import SESSION_COUNT, RECOMMENDATION_COUNT, MODEL_INFERENCE_LATENCY, TimerContextManager
from typing import List
from datetime import datetime, timedelta 

router = APIRouter(
    prefix="/sessions",
    tags=["behavior"]
)

@router.post("/log", response_model=SessionLog)
async def log_session(session: SessionLogCreate, db: Session = Depends(get_db)):
    """
    Log a study session with behavior data
    """

    # Increment session count metric
    SESSION_COUNT.inc()

    # Convert to DB model
    db_session = SessionLogModel(
        user_id=int(session.userId),
        start_time=session.startTime,
        end_time=session.endTime,
        pages_read=session.pagesRead,
        focus_rating=session.focusRating,
        completed=session.completed,
        device=session.device,
        timezone=session.timezone
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return SessionLog(
        logID = db_session.log_id,
        userId = str(db_session.user_id),
        startTime = db_session.start_time,
        endTime = db_session.end_time,
        pagesRead = db_session.pages_read,
        focusRating = db_session.focus_rating,
        completed = db_session.completed,
        device = db_session.device,
        timezone = db_session.timezone,
        createdAt = db_session.created_at
    )

@router.get("/recommendations", response_model=RecommendationResponse)
async def get_session_recommendations(userId: str, db: Session = Depends(get_db)):
    """
    Get personalized study session recommendations
    """

    # Increment recommendation count metric
    RECOMMENDATION_COUNT.inc()

    # Check if user exists
    user_id = int(userId)

    # Get recommendations from ML module with timing
    with TimerContextManager(MODEL_INFERENCE_LATENCY, ["recommendation"]):
        recommendations = get_recommendations(user_id, db)

    # If no recommendations could be generated
    if not recommendations:
        raise HTTPException(status_code=404, detail="Not enough data to generate recommendations for this user")


