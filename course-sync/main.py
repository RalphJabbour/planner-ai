#!/usr/bin/env python
"""
Main entry point for the course sync service.
Runs the synchronization job on a schedule.
"""
import os
import time
import logging
import signal
import sys
from datetime import datetime
from sync import sync_courses
from scraper import scrape_all_courses

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag to control the main loop
should_continue = True

def signal_handler(sig, frame):
    """Handle termination signals properly"""
    global should_continue
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    should_continue = False
    sys.exit(0)

def sync_job():
    """Run the course synchronization job"""
    try:
        logger.info(f"Starting course synchronization at {datetime.now().isoformat()}")
        
        # Step 1: Scrape course data
        courses_df = scrape_all_courses()
        
        # Step 2: Sync with database
        if courses_df is not None and not courses_df.empty:
            # Convert DataFrame to list of dictionaries
            courses_list = courses_df.to_dict(orient='records') 
            logger.info(f"Retrieved {len(courses_list)} courses to sync")
            print(courses_list[0])  # Debugging line to check the first course
            stats = sync_courses(courses_list)
            logger.info(f"Synchronization complete: {stats}")
        else:
            logger.warning("No course data retrieved, skipping sync")
            
    except Exception as e:
        logger.error(f"Error in sync job: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get interval from environment or default to 5 minutes
    interval = int(os.getenv("SYNC_INTERVAL", "300"))
    
    logger.info(f"Course sync service starting, will run every {interval} seconds")
    
    last_run = 0
    
    # Run once at startup
    sync_job()
    last_run = time.time()
    
    # Simple time-based scheduling loop
    while should_continue:
        current_time = time.time()
        if current_time - last_run >= interval:
            sync_job()
            last_run = current_time
        
        # Short sleep to prevent high CPU usage
        time.sleep(1)