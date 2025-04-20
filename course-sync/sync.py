#!/usr/bin/env python
"""
Database synchronization module.
Handles the efficient updating of course data in the database.
"""

import os
import logging
from sqlalchemy import Column, create_engine, String, Integer, TIMESTAMP, JSON, text
from sqlalchemy.orm import Session
from datetime import datetime, timezone # Import timezone
from typing import List, Dict, Any
from sqlalchemy.ext.declarative import declarative_base

# Define the base class for SQLAlchemy models
Base = declarative_base()

class Course(Base):
    __tablename__ = "courses"
    
    course_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_code = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    course_CRN = Column(Integer, unique=True, nullable=False)
    course_section = Column(Integer, nullable=False)
    course_credits = Column(Integer, nullable=False)
    actual_enrollment = Column(Integer, nullable=False)
    max_enrollment = Column(Integer, nullable=False)
    instructor = Column(String)
    semester = Column(String, nullable=False)
    timetable = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


# Configure logging
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@db:5432/EECE503N-planner")

def transform_course_data(scraped_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform scraped course data into the format expected by the database model.
    
    Args:
        scraped_courses: List of dictionaries with raw course information from scraper
    
    Returns:
        List of dictionaries formatted to match the Course database model
    """
    transformed_courses = []
    
    for course in scraped_courses:
        if course.get('term') == 'Term':
            continue
        # Create timetable JSON structure for days/times
        timetable = {
            "times": []
        }
        
        # First time slot (if not empty)
        if course.get('begin_time_1') and course.get('begin_time_1') != '.':
            days = []
            for day_key in ['s', 'c', 'h', 'e', 'd', 'u', 'le_1']:
                if day_key in course and course[day_key] != '.':
                    days.append(course[day_key])
                    
            timetable["times"].append({
                "days": "".join(days),
                "start_time": course.get('begin_time_1', ''),
                "end_time": course.get('end_time__1', ''),
                "building": course.get('building_1', ''),
                "room": course.get('room_1', '')
            })
        
        # Second time slot (if exists)
        if course.get('begin_time_2') and course.get('begin_time_2') != '.':
            days = []
            for day_key in ['s_1', 'c_1', 'h_1', 'e_1', 'd_1', 'u_1', 'le_2']:
                if day_key in course and course[day_key] != '.':
                    days.append(course[day_key])
                    
            timetable["times"].append({
                "days": "".join(days),
                "start_time": course.get('begin_time_2', ''),
                "end_time": course.get('end_time__2', ''),
                "building": course.get('building_2', ''),
                "room": course.get('room_2', '')
            })
        
        # Build instructor name
        instructor = "TBA"
        if course.get('instructor_fname') and course.get('instructor_surame'):  
            instructor = f"{course['instructor_fname']} {course['instructor_surame']}"
        
        # Handle potential empty values safely
        try:
            actual_enrollment = int(course.get('actual_enrolment', 0))
        except (ValueError, TypeError):
            actual_enrollment = 0
            
        try:
            seats_available = int(course.get('seats_available', 0))
        except (ValueError, TypeError):
            seats_available = 0
            
        try:
            course_credits = int(course.get('credit_hours', 0))
        except (ValueError, TypeError):
            course_credits = 0
            
        try:
            course_section = int(course.get('section', 1))
        except (ValueError, TypeError):
            course_section = 1
            
        try:
            course_crn = int(course.get('c_r_n', 0))
        except (ValueError, TypeError):
            course_crn = 0
        
        # Create a course object that matches our database model
        transformed_course = {
            "course_code": f"{course.get('subject', '')}{course.get('code', '')}",
            "course_name": course.get('title', ''),
            "course_CRN": course_crn,
            "course_section": course_section,
            "course_credits": course_credits,
            "actual_enrollment": actual_enrollment,
            "max_enrollment": actual_enrollment + seats_available,
            "instructor": instructor,
            "semester": course.get('term', ''),
            "timetable": timetable
        }
        
        transformed_courses.append(transformed_course)
        
    return transformed_courses

def sync_courses(new_courses: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Efficiently synchronize courses in the database.
    
    Args:
        new_courses: List of dictionaries with course information from scraper
    
    Returns:
        Dictionary with stats about the synchronization operation
    """
    # {'term': 'Term', 'c_r_n': 'C R N', 'subject': 'Subject', 'code': 'Code', 'section': 'Section', 'title': 'Title', 'credit_hours': 'Credit Hours', 'billing_hours': 'BILLING HOURS', 'college': 'COLLEGE', 'actual_enrolment': 'ACTUAL ENROLMENT', 'seats_available': 'SEATS AVAILABLE', 'begin_time_1': 'BEGIN TIME 1', 'end_time__1': 'END TIME  1', 'building_1': 'BUILDING 1', 'room_1': 'Room 1', 's': 'S', 'c': 'C', 'h': 'H', 'e': 'E', 'd': 'D', 'u': 'U', 'le_1': 'LE 1', 'begin_time_2': 'BEGIN TIME 2', 'end_time__2': 'END TIME  2', 'building_2': 'BUILDING 2', 'room_2': 'Room 2', 's_1': 'S', 'c_1': 'C', 'h_1': 'H', 'e_1': 'E', 'd_1': 'D', 'u_1': 'U', 'le_2': 'LE 2', 'instructor_fname': 'Instructor F.Name', 'instructor_surame': 'Instructor Surame', 'linked_crn': 'Linked CRN', 'instructional_method': 'Instructional Method'}
    # {'term': 'Summer 2024-2025(202530)', 'c_r_n': '30014', 'subject': 'ACCT', 'code': '215', 'section': '1', 'title': 'Management Accounting', 'credit_hours': '3', 'billing_hours': '3', 'college': 'SB', 'actual_enrolment': '27', 'seats_available': '1', 'begin_time_1': '1100', 'end_time__1': '1215', 'building_1': 'OSB', 'room_1': '233', 's': 'M', 'c': 'T', 'h': 'W', 'e': 'R', 'd': '.', 'u': '.', 'le_1': '.', 'begin_time_2': '.', 'end_time__2': '.', 'building_2': '.', 'room_2': '.', 's_1': '.', 'c_1': '.', 'h_1': '.', 'e_1': '.', 'd_1': '.', 'u_1': '.', 'le_2': '.', 'instructor_fname': 'Abdeljalil', 'instructor_surame': 'Ghanem', 'linked_crn': '', 'instructional_method': ''}
    # the above line is a row of what we are receiving in new_courses
    # run through all of them and transform them to the course model
    
    new_courses = transform_course_data(new_courses)

    logger.info(f"Connecting to database: {DATABASE_URL}")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        with Session(engine) as db:
            # Step 1: Create a dictionary of existing courses by code for quick lookups
            existing_courses = {}
            for course in db.query(Course).all():
                existing_courses[course.course_CRN] = course
            
            logger.info(f"Found {len(existing_courses)} existing courses in database")
            
            # Step 2: Track codes for deletion and update checking
            new_course_CRNs = set()
            courses_to_add = []
            courses_updated = 0
            
            # Step 3: Process each new course
            for course_data in new_courses:
                course_CRN = course_data["course_CRN"]
                new_course_CRNs.add(course_CRN)
                
                if course_CRN in existing_courses:
                    # Update existing course if needed
                    existing = existing_courses[course_CRN]
                    
                    # Use direct attribute dictionary to check and update
                    needs_update = False
                    for key, value in course_data.items():
                        # Skip the course_CRN since we use it for identification
                        if key == "course_CRN":
                            continue
                        
                        # Check if the attribute exists on the course model and needs updating
                        # Convert types if necessary (e.g., string from scraper to int in model)
                        current_value = getattr(existing, key, None)
                        target_type = type(current_value) if current_value is not None else None
                        
                        # Attempt type conversion for common cases like int/str mismatches
                        converted_value = value
                        if target_type and not isinstance(value, target_type):
                            try:
                                converted_value = target_type(value)
                            except (ValueError, TypeError):
                                logger.warning(f"Could not convert value '{value}' to type {target_type} for key '{key}' in CRN {course_CRN}")
                                continue # Skip this field if conversion fails

                        if hasattr(existing, key) and current_value != converted_value:
                            setattr(existing, key, converted_value)
                            needs_update = True
                            
                    if needs_update:
                        # updated_at is handled by onupdate=datetime.now(timezone.utc)
                        courses_updated += 1
                else:
                    # Prepare data for new course, attempting type conversions
                    new_course_data = {}
                    for key, value in course_data.items():
                         if hasattr(Course, key): # Check if the key exists in the Course model
                            column_type = type(getattr(Course, key).type.python_type())
                            try:
                                new_course_data[key] = column_type(value)
                            except (ValueError, TypeError):
                                 # Handle cases like empty strings for integer fields
                                if column_type is int and value == '':
                                    new_course_data[key] = 0 # Or None if nullable
                                else:
                                    logger.warning(f"Could not convert value '{value}' to type {column_type} for key '{key}' in new CRN {course_CRN}")
                                    # Decide how to handle: skip field, use default, etc.
                                    # For now, let's skip if not CRN
                                    if key != "course_CRN":
                                        continue
                                    else: # CRN is essential, raise or log error
                                         logger.error(f"CRN conversion failed for value '{value}'. Skipping course.")
                                         continue # Skip adding this course if CRN fails conversion


                    # Create new course object only if CRN is valid
                    if "course_CRN" in new_course_data:
                        new_course = Course(**new_course_data)
                        # created_at and updated_at are handled by defaults/onupdate
                        courses_to_add.append(new_course)

            # Step 4: Find courses to delete (course_CRNs in database but not in new data)
            CRNs_to_delete = set(existing_courses.keys()) - new_course_CRNs
            deleted_count = 0
            
            # Step 5: Perform database operations in a safe order
            if CRNs_to_delete:
                # Corrected to filter by course_CRN
                deleted_count = db.query(Course).filter(
                    Course.course_CRN.in_(CRNs_to_delete) 
                ).delete(synchronize_session=False)
                
                logger.info(f"Deleted {deleted_count} courses no longer in source data")
            
            # Add all new courses
            if courses_to_add:
                db.add_all(courses_to_add)
                logger.info(f"Adding {len(courses_to_add)} new courses")
                
            # Commit all changes in a single transaction
            db.commit()
            
            # Corrected total_in_db calculation
            total_in_db_after_sync = len(existing_courses) + len(courses_to_add) - deleted_count

            # Return stats for logging
            return {
                "added": len(courses_to_add),
                "updated": courses_updated,
                "deleted": deleted_count,
                "total_checked_from_source": len(new_course_CRNs),
                "total_in_db_after_sync": total_in_db_after_sync 
            }
            
    except Exception as e:
        logger.error(f"Database error during sync: {str(e)}", exc_info=True)
        # Rollback in case of error during commit
        if 'db' in locals() and db.is_active:
             db.rollback()
        return {"error": str(e)}