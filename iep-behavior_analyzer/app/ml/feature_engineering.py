from sqlalchemy.orm import Session
from app.models.behavior import SessionLog, FeatureAggregate
from datetime import datetime, timedelta 
import pandas as pd
import numpy as np

def calculate_session_features(logs_df):
    """
    Calculate derived features from raw session logs
    """
    if logs_df.empty:
        return pd.DataFrame()
    
    # Calculate session duration in minutes
    logs_df['duration'] = (logs_df['end_time'] - logs_df['start_time']).dt.total_seconds() / 60

    # Calculate reading speed in (pages per minute)
    logs_df['speed'] = logs_df['pages_read'] / logs_df['duration']

    # Calculate efficiency score
    logs_df['efficiency'] = logs_df['speed'] * logs_df['focus_rating']

    # Extract time of day bucket (hour)
    logs_df["time_of_day_bucket"] = logs_df["start_time"].dt.hour

    return logs_df

def compute_user_aggregates(user_id, db: Session):
    """
    Compute rolling aggregates per user (7-day, 30-day)
    """
    # Get all session logs for user
    logs = db.query(SessionLog).filter(SessionLog.user_id == user_id).all()

    if not logs:
        return None 
    
    # Convert to DataFrame
    logs_df = pd.DataFrame([{
        'log_id': log.log_id,
        'user_id': log.user_id,
        'start_time': log.start_time,
        'end_time': log.end_time,
        'pages_read': log.pages_read,
        'focus_rating': log.focus_rating
    } for log in logs])

    # Calculate features
    logs_df = calculate_session_features(logs_df)

    if logs_df.empty:
        return None 

    # Current date
    now = datetime.now()

    # 7-day window
    logs_7d = logs_df[logs_df['start_time'] >= (now - timedelta(days=7))]
    # 30-day window
    logs_30d = logs_df[logs_df['start_time'] >= (now-timedelta(days=30))]

    # Compute aggregates
    agg_7d = {
        'avg_duration_7d': logs_7d['duration'].mean() if not logs_7d.empty else None,
        'avg_efficiency_7d': logs_7d['efficiency'].mean() if not logs_7d.empty else None,
        'completion_rate_7d': logs_7d['completed'].mean() if not logs_7d.empty else None
    }

    agg_30d = {
        'avg_duration_30d': logs_30d['duration'].mean() if not logs_30d.empty else None,
        'avg_efficiency_30d': logs_30d['efficiency'].mean() if not logs_30d.empty else None,
        'completion_rate_30d': logs_30d['completed'].mean() if not logs_30d.empty else None 
    }

    # Combine
    aggregates = {**agg_7d, **agg_30d}

    # Store in databse
    db_agg = FeatureAggregate(
        user_id=user_id,
        date=now,
        **aggregates
    )

    db.add(db_agg)
    db.commit()

    return aggregates
