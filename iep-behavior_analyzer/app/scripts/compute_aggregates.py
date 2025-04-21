"""
Script to compute user aggregates for behavior analysis.
This can be run as a cron job.
"""
import os 
import sys 
import logging 
from datetime import datetime 

# Set up logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='aggregate_computation.log'
)

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal 
from app.ml.feature_engineering import compute_user_aggregates 
from sqlalchemy.orm import text 

def main():
    """Main function to compute aggregates for all users"""
    start_time = datetime.now()
    logging.info("Starting aggregate computation at {start_time}")

    # Get database session
    db = SessionLocal()
    try:
        # Get all user IDs
        result = db.execute(text("SELECT student_id FROM students"))
        user_ids = [row[0] for row in result]

        logging.info(f"Found {len(user_ids)} users to process")

        # Compute aggregates for each user
        for i, user_id in enumerate(user_ids):
            try:
                compute_user_aggregates(user_id, db)
                if (i+1) % 100 == 0:
                    logging.info(f"Processed {i+1}/{len(user_ids)} users")
            except Exception as e:
                logging.error(f"Error computing aggregates for user {user_id}: {e}")
        
        logging.info(f"Computed aggregates for {len(user_ids)} users")

    except Exception as e:
        logging.error(f"Error computing aggregates: {e}")
        raise 
    finally:
        db.close()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logging.info(f"Aggregate computation completed in {duration:.2f} seconds")

if __name__ == "__main__":
    main()
