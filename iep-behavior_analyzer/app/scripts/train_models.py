#! /usr/bin/env python3
"""
Script to train machine learning models for behavior analysis.
This can be run as a cron job.
"""

import os
import sys
import logging 
from datetime import datetime 

# Set up logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='model_training.log'
)

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal
from app.ml.model_training import train_models 

def main():
    """Main function to train models"""
    start_time = datetime.now()
    logging.info("Starting model training at {start_time}")

    # Get database session 
    db = SessionLocal()
    try:
        # Train the models
        result = train_models(db)
        if result:
            logging.info(f"Model training completed successfully: {result}")
        else:
            logging.warning("Not enough data to train models")
        
    except Exception as e:
        logging.error(f"Error training models: {e}")
        raise 
    finally:
        db.close()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logging.info(f"Model training completed in {duration:.2f} seconds")

if __name__ == "__main__":
    main()