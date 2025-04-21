from celery import Celery
from app.database import SessionLocal
from app.ml.model_training import train_models 
from app.ml.feature_engineering import compute_user_aggregates 
from sqlalchemy import text
import os 

# Configure Celery
celery_app = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

@celery_app.task
def train_models_task():
    """
    Task to train ML models on a schedule
    """
    db = SessionLocal()
    try:
        # Train models
        result = train_models(db)
        return result 
    finally:
        db.close()

@cerely_app.task
def compute_user_aggregates_task():
    """
    Task to compute user aggregates for all users
    """
    db = SessionLocal()
    try:
        # Get all user IDs
        result = db.execute(text("SELECT id FROM users"))
        user_ids = [row[0] for row in result]

        # Compute aggregates for each user
        for user_id in user_ids:
            compute_user_aggregates(user_id, db)
        
        return f"Computed aggregates for {len(user_ids)} users"
    finally:
        db.close()