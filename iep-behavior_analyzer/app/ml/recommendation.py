from sqlalchemy.orm import Session
from app.models.behavior import SessionLog, FeatureAggregate
from app.ml.model_training import get_latest_models 
from app.ml.feature_engineering import calculate_session_features 
import pandas as pd
import numpy as np
from datetime import datetime, timedelta 
from collections import defaultdict 

def get_user_peak_hours(user_id, db: Session):
    """
    Get the user's top 3 most efficient hours
    """
    # Get all logs for user
    logs = db.query(SessionLog).filter(SessionLog.user_id == user_id).all()

    if not logs:
        return [9, 14, 19] # Default peak hours if no data
    
    # Convert to DataFrame
    logs_df = pd.DataFrame([{
        'start_time': log.start_time,
        'end_time': log.end_time,
        'pages_read': log.pages_read,
        'focus_rating': log.focus_rating,
    } for log in logs])

    # Calculate features
    logs_df = calculate_session_features(logs_df)

    if logs_df.empty:
        return [9, 14, 19] # Default peak hours if no data
    
    # Group by hour and get average efficiency
    hour_efficiency = logs_df.groupby(logs_df['start_time'].dt.hour)['efficiency'].mean()

    # Get top 3 hours
    if len(hour_efficiency) >= 3:
        peak_hours = hour_efficiency.sort_values(ascending=False).index[:3].tolist()
    else:
        # If not enough data, fill with reasonable defaults
        existing_hours = hour_efficiency.sort_values(ascending=False).index.tolist()
        default_hours = [9, 14, 19]
        peak_hours = existing_hours + [h for h in default_hours if h not in existing_hours][:3-len(existing_hours)]

    
    return peak_hours 

def generate_candidate_slots(user_id, db: Session):
    """
    Generate candidate time slots for study sessions
    """
    # Get peak hours for the user
    peak_hours = get_user_peak_hours(user_id, db)

    # Get current date
    now = datetime.now()

    # Generate slots for next 7 days
    candidates = []
    for day in range(7):
        date = now.date() + timedelta(days=day)
        for hour in range(8, 22): # 8am to 10pm
            # Give higher priority to peak hours
            priority = 3 if hour in peak_hours else 1

            # Generate different durations
            for duration in [20, 30, 45, 60]:
                slot_start = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour)
                candidates.append({
                    'start_time': slot_start,
                    'duration': duration,
                    'hour': hour,
                    'day_of_week': slot_start.weekday(),
                    'priority': priority
                })

    return candidates, peak_hours 

def get_recommendations(user_id, db: Session):
    """
    Generate personalized study session recommendations
    """
    # Load trained models
    reg_model, clf_model = get_latest_models()

    # If models don't exist yet, return default recommendation
    if reg_model is None or clf_model is None:
        # Default recommendation (without model predictions)
        now = datetime.now()
        start_tomorrow = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)

        return {
            "recommendedStart": start_tomorrow,
            "recommendedDuration": 45,
            "predictedEfficiency": 0.75,
            "predictedCompletionProb": 0.8,
            "peakHours": get_user_peak_hours(user_id, db),
        }
    
    # Generate candidate slots
    candidates, peak_hours = generate_candidate_slots(user_id, db)

    # Prepare features for prediction
    candidates_df = pd.DataFrame(candidates)
    candidates_df['user_id_cat'] = user_id 

    # These need to match the features used during training
    features = ['user_id_cat', 'hour', 'day_of_week', 'duration']

    # Predict efficiency and completion probability for each slot
    candidates_df['predicted_efficiency'] = reg_model.predict(candidates_df[features])
    candidates_df['predicted_completion'] = clf_model.predict_proba(candidates_df[features])[:, 1]
    
    # Calculate expected utility
    candidates_df['utility'] = candidates_df['predicted_efficiency'] * candidates_df['predicted_completion'] * candidates_df['priority']

    # Find the slot with highest utility
    best_slot = candidates_df.loc[candidates_df['utility'].idxmax()]

    return {
        "recommendedStart": best_slot['start_time'],
        "recommendedDuration": int(best_slot['duration']),
        "predictedEfficiency": float(best_slot['predicted_efficiency']),
        "predictedCompletionProb": float(best_slot['predicted_completion']),
        "peakHours": peak_hours
    }
