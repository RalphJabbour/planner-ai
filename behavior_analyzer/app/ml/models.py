import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.linear_model import LinearRegression 
from app.ml.feature_extraction import FeatureExtractor 
from app.models.reflected_models import ProductivityProfile, SessionEvent
from app.schemas.behavior import DataPackageRequest, ProductivityProfileData
import datetime
from sqlalchemy.orm import Session

class BehaviorModel:
    """
    Manages modeling and prediction components of the Behavior Analyzer
    """

    def __init__(self, db: Session):
        """Initialize with either a database session or a data package"""
        if hasattr(db, 'sessions'):
            # It's a DataPackageRequest
            self.sessions = db.sessions
            self.context_signals = db.context_signals
            self.profile = db.profile
            self.feature_extractor = FeatureExtractor(self.sessions, self.context_signals)
        else:
            # It's a database session
            self.db = db
            self.profile = None  # Initialize profile to None
            self.feature_extractor = FeatureExtractor(db)
    
    def get_or_create_profile(self, student_id: int) -> ProductivityProfileData:
        """
        Gets the existing profile or creates a new one with default values and saves it to the database
        """

        # Check if profile exists in instance or fetch from database
        if hasattr(self, 'profile') and self.profile and self.profile.student_id == student_id:
            return self.profile
        
        # If we have a database session, try to fetch the profile
        if hasattr(self, 'db'):
            db_profile = self.db.query(ProductivityProfile).filter(ProductivityProfile.student_id == student_id).first()
            if db_profile:
                # Convert to dictionary first, then to schema model
                profile_dict = {
                    "profile_id": db_profile.profile_id,
                    "student_id": db_profile.student_id,
                    "slot_weights": db_profile.slot_weights,
                    "peak_windows": db_profile.peak_windows,
                    "max_continuous_minutes": db_profile.max_continuous_minutes,
                    "ideal_break_minutes": db_profile.ideal_break_minutes,
                    "efficiency_decay_rate": db_profile.efficiency_decay_rate,
                    "fatigue_factor": db_profile.fatigue_factor,
                    "recovery_factor": db_profile.recovery_factor,
                    "day_multipliers": db_profile.day_multipliers,
                    "soft_obligation_buffer": db_profile.soft_obligation_buffer,
                    "retention_rates": db_profile.retention_rates,
                    "last_updated": db_profile.last_updated
                }
                self.profile = ProductivityProfileData(**profile_dict)
                return self.profile
            
            # Profile doesn't exist, create and save to database
            default_days = {
                'Monday': 1.0, 'Tuesday': 1.0, 'Wednesday': 1.0, 
                'Thursday': 1.0, 'Friday': 1.0, 'Saturday': 1.0, 'Sunday': 1.0
            }
            
            # Create the database model instance
            new_db_profile = ProductivityProfile(
                student_id=student_id,
                slot_weights={},
                peak_windows=[],
                max_continuous_minutes=45,
                ideal_break_minutes=10,
                efficiency_decay_rate=0.05,
                fatigue_factor=0.15,
                recovery_factor=0.2,
                day_multipliers=default_days,
                soft_obligation_buffer=30,
                retention_rates={},
                last_updated=datetime.datetime.now(datetime.timezone.utc)
            )
            
            # Add to database and commit
            self.db.add(new_db_profile)
            self.db.commit()
            self.db.refresh(new_db_profile)
            
            # Convert to dictionary first, then to schema model
            profile_dict = {
                "profile_id": new_db_profile.profile_id,
                "student_id": new_db_profile.student_id,
                "slot_weights": new_db_profile.slot_weights,
                "peak_windows": new_db_profile.peak_windows,
                "max_continuous_minutes": new_db_profile.max_continuous_minutes,
                "ideal_break_minutes": new_db_profile.ideal_break_minutes,
                "efficiency_decay_rate": new_db_profile.efficiency_decay_rate,
                "fatigue_factor": new_db_profile.fatigue_factor,
                "recovery_factor": new_db_profile.recovery_factor,
                "day_multipliers": new_db_profile.day_multipliers,
                "soft_obligation_buffer": new_db_profile.soft_obligation_buffer,
                "retention_rates": new_db_profile.retention_rates,
                "last_updated": new_db_profile.last_updated
            }
            self.profile = ProductivityProfileData(**profile_dict)
            return self.profile
        
        # If no database session, just return in-memory profile
        default_days = {
            'Monday': 1.0, 'Tuesday': 1.0, 'Wednesday': 1.0, 
            'Thursday': 1.0, 'Friday': 1.0, 'Saturday': 1.0, 'Sunday': 1.0
        }
        
        new_profile = ProductivityProfileData(
            profile_id=0,
            student_id=student_id,
            slot_weights={},
            peak_windows=[],
            max_continuous_minutes=45,
            ideal_break_minutes=10,
            efficiency_decay_rate=0.05,
            fatigue_factor=0.15,
            recovery_factor=0.2,
            day_multipliers=default_days,
            soft_obligation_buffer=30,
            retention_rates={},
            last_updated=datetime.datetime.now(datetime.timezone.utc)
        )
        
        self.profile = new_profile
        return new_profile
    
    def update_profile(self, student_id: int, force_update: bool = False) -> ProductivityProfileData:
        """
        Updates the productivity profile with latest behavior data and persists to database
        """
        profile = self.get_or_create_profile(student_id)

        # Extract features
        slot_efficiencies = self.feature_extractor.extract_slot_efficiency(student_id)
        peak_windows = self.feature_extractor.identify_peak_windows(slot_efficiencies)
        session_params = self.feature_extractor.compute_session_parameters(student_id)
        fatigue_params = self.feature_extractor.compute_fatigue_recovery(student_id)
        adjustment_factors = self.feature_extractor.compute_adjustment_factors(student_id)
        retention_rates = self.feature_extractor.compute_retention_indicators(student_id)

        # Create updated profile
        updated_profile = ProductivityProfileData(
            profile_id=profile.profile_id,
            student_id=profile.student_id,
            slot_weights=slot_efficiencies,
            peak_windows=peak_windows,
            max_continuous_minutes=session_params["max_continuous_minutes"],
            ideal_break_minutes=session_params["ideal_break_minutes"],
            efficiency_decay_rate=session_params["efficiency_decay_rate"],
            fatigue_factor=fatigue_params["fatigue_factor"],
            recovery_factor=fatigue_params["recovery_factor"],
            day_multipliers=adjustment_factors["day_multipliers"],
            soft_obligation_buffer=adjustment_factors["soft_obligation_buffer"],
            retention_rates=retention_rates,
            last_updated=datetime.datetime.now(datetime.timezone.utc)
        )
        
        # Save to database if we have a db session
        if hasattr(self, 'db'):
            # Find existing profile in database
            db_profile = self.db.query(ProductivityProfile).filter(
                ProductivityProfile.student_id == student_id
            ).first()
            
            if db_profile:
                # Update existing profile
                db_profile.slot_weights = slot_efficiencies
                db_profile.peak_windows = peak_windows
                db_profile.max_continuous_minutes = session_params["max_continuous_minutes"]
                db_profile.ideal_break_minutes = session_params["ideal_break_minutes"]
                db_profile.efficiency_decay_rate = session_params["efficiency_decay_rate"]
                db_profile.fatigue_factor = fatigue_params["fatigue_factor"]
                db_profile.recovery_factor = fatigue_params["recovery_factor"]
                db_profile.day_multipliers = adjustment_factors["day_multipliers"]
                db_profile.soft_obligation_buffer = adjustment_factors["soft_obligation_buffer"]
                db_profile.retention_rates = retention_rates
                db_profile.last_updated = datetime.datetime.now(datetime.timezone.utc)
            else:
                # Create new profile
                new_db_profile = ProductivityProfile(
                    student_id=student_id,
                    slot_weights=slot_efficiencies,
                    peak_windows=peak_windows,
                    max_continuous_minutes=session_params["max_continuous_minutes"],
                    ideal_break_minutes=session_params["ideal_break_minutes"],
                    efficiency_decay_rate=session_params["efficiency_decay_rate"],
                    fatigue_factor=fatigue_params["fatigue_factor"],
                    recovery_factor=fatigue_params["recovery_factor"],
                    day_multipliers=adjustment_factors["day_multipliers"],
                    soft_obligation_buffer=adjustment_factors["soft_obligation_buffer"],
                    retention_rates=retention_rates,
                    last_updated=datetime.datetime.now(datetime.timezone.utc)
                )
                self.db.add(new_db_profile)
            
            # Commit changes
            self.db.commit()
        
        self.profile = updated_profile
        return updated_profile

    def predict_session_success(self, student_id: int, start_time: pd.Timestamp, duration: int) -> Dict[str, float]:
        """
        Predicts likelihood of session successful completion and expected efficiency
        """
        profile = self.get_or_create_profile(student_id)

        #Extract day and hour
        day = start_time.strftime("%A")
        hour = start_time.hour 

        # Get slot efficiency
        slot_key = f"{day}-{hour}"
        slot_efficiency = profile.slot_weights.get(slot_key, 0.5) # Default to 0.5 if unknown

        # Apply day multiplier
        day_multiplier = profile.day_multipliers.get(day, 1.0)

        # Check if duration exceeds optimal continuous time
        optimal_duration = profile.max_continuous_minutes
        if duration > optimal_duration:
            # Apply efficiency decay
            minutes_over = duration - optimal_duration
            decay_factor = 1.0 - (minutes_over * profile.efficiency_decay_rate)
            decay_factor = max(decay_factor, 0.4) # Don't let it go below 40%
        else:
            decay_factor = 1.0 
        
        # Calculated predicted efficiency
        predicted_efficiency = slot_efficiency * day_multiplier * decay_factor 

        # Calculate completion probability based on efficiency
        completion_probability = min(0.5 + predicted_efficiency * 0.5, 0.95)

        # Build prediction result
        prediction = {
            "predicted_efficiency": round(predicted_efficiency, 2),
            "completion_probability": round(completion_probability, 2),
            "expected_overrun": 0
        }

        # Add predicted time overrun 
        if predicted_efficiency < 0.7:
            # Lower efficiency may lead to time overrun
            expected_overrun = int((1 / predicted_efficiency - 1) * duration * 0.5)
            prediction["expected_overrun"] = min(expected_overrun, duration) # Cap at least 100% overrun

        return prediction 
    
    def recommend_slots(self, student_id: int, task_duration: int, lookahead_days: int = 7) -> List[Dict]:
        """
        Recommends optimal time slots for a task based on the productivity profile
        """
        profile = self.get_or_create_profile(student_id)

        # Use timezone-aware datetime
        today = pd.Timestamp.now(tz='UTC').normalize()

        # Generate all possible slots for the next lookahead_days
        all_slots = []
        for day_offset in range(lookahead_days):
            day_date = today + pd.Timedelta(days=day_offset)
            day_name = day_date.strftime("%A")

            # Apply day multiplier
            day_multiplier = profile.day_multipliers.get(day_name, 1.0)

            for hour in range(7, 22): # 7am to 10pm
                slot_key = f"{day_name}-{hour}"
                base_efficiency = profile.slot_weights.get(slot_key, 0.5) # Default to moderate if no data

                # Apply day multiplier
                adjusted_efficiency = base_efficiency * day_multiplier 

                # Check if this slot can fit the requested duration
                # For simplicity, assume each slot is 1 hour
                slot = {
                    "day": day_name,
                    "day_date": day_date.strftime("%Y-%m-%d"),
                    "start_hour": hour,
                    "end_hour": hour + 1,
                    "efficiency": round(adjusted_efficiency, 2),
                    "can_fit": hour + (task_duration / 60) <= 22 # Check if it fits before 10pm
                }

                if slot["can_fit"]:
                    all_slots.append(slot)
        
        # Sort by efficiency and filter
        recommended_slots = sorted(all_slots, key=lambda x: x["efficiency"], reverse=True)

        # Take top slots (at most 5)
        return recommended_slots[:5]

    def initialize_cold_start(self, student_id: int, preferences: Dict = None) -> ProductivityProfileData:
        """
        Initializes a productivity profile for a new student with cold start preferences and stores in the database
        """
        # Get the existing profile or create a new default one
        profile = self.get_or_create_profile(student_id)
        
        # Default slot weights based on common patterns
        default_slot_weights = {}
        
        # Morning peak: 9-11 AM
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            for hour in range(9, 12):
                default_slot_weights[f"{day}-{hour}"] = 0.8
                
        # Afternoon dip: 2-3 PM
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            for hour in range(14, 16):
                default_slot_weights[f"{day}-{hour}"] = 0.6
                
        # Evening recovery: 7-9 PM
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            for hour in range(19, 22):
                default_slot_weights[f"{day}-{hour}"] = 0.75
                
        # Weekend morning: generally good for focused work
        for day in ['Saturday', 'Sunday']:
            for hour in range(10, 13):
                default_slot_weights[f"{day}-{hour}"] = 0.85
        
        # Fill in the rest with moderate values
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            for hour in range(7, 23):
                slot_key = f"{day}-{hour}"
                if slot_key not in default_slot_weights:
                    default_slot_weights[slot_key] = 0.65
        
        # Apply preferences if available
        if preferences:
            if 'preferred_study_time' in preferences:
                pref = preferences['preferred_study_time']
                
                # Boost preferred times
                if pref == 'morning':
                    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        for hour in range(7, 12):
                            slot_key = f"{day}-{hour}"
                            default_slot_weights[slot_key] = min(default_slot_weights.get(slot_key, 0) + 0.15, 0.95)
                
                elif pref == 'afternoon':
                    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        for hour in range(12, 18):
                            slot_key = f"{day}-{hour}"
                            default_slot_weights[slot_key] = min(default_slot_weights.get(slot_key, 0) + 0.15, 0.95)
                
                elif pref == 'evening':
                    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        for hour in range(18, 23):
                            slot_key = f"{day}-{hour}"
                            default_slot_weights[slot_key] = min(default_slot_weights.get(slot_key, 0) + 0.15, 0.95)
        
        # Create peak windows from top slots
        top_slots = sorted(
            [(k, v) for k, v in default_slot_weights.items()], 
            key=lambda x: x[1], 
            reverse=True
        )[:15]
        
        # Identify windows
        peak_windows = []
        for slot, efficiency in top_slots:
            day, hour = slot.split("-")
            hour = int(hour)
            
            # Find existing window
            found = False
            for window in peak_windows:
                if window["day"] == day and window["end_hour"] == hour:
                    # Extend window
                    window["start_hour"] = hour
                    found = True
                    break
                elif window["day"] == day and window["start_hour"] == hour + 1:
                    # Prepend to window
                    window["start_hour"] = hour
                    found = True
                    break
            
            if not found:
                # Create new window
                peak_windows.append({
                    "day": day,
                    "start_hour": hour,
                    "end_hour": hour + 1,
                    "efficiency": efficiency
                })
        
        # Update the profile
        new_profile = ProductivityProfileData(
            profile_id=profile.profile_id,
            student_id=profile.student_id,
            slot_weights=default_slot_weights,
            peak_windows=peak_windows,
            max_continuous_minutes=45,
            ideal_break_minutes=10,
            efficiency_decay_rate=0.05,
            fatigue_factor=0.15,
            recovery_factor=0.2,
            day_multipliers=profile.day_multipliers,
            soft_obligation_buffer=30,
            retention_rates=self.feature_extractor.compute_retention_indicators(student_id),
            last_updated=datetime.datetime.now(datetime.timezone.utc)
        )

        self.profile = new_profile
        
        # Only add this block at the end - store to database
        if hasattr(self, 'db'):
            # Convert to database model
            db_profile = self.db.query(ProductivityProfile).filter(
                ProductivityProfile.student_id == student_id
            ).first()
            
            if db_profile:
                # Update existing record
                db_profile.slot_weights = new_profile.slot_weights
                db_profile.peak_windows = new_profile.peak_windows
                db_profile.max_continuous_minutes = new_profile.max_continuous_minutes
                db_profile.ideal_break_minutes = new_profile.ideal_break_minutes
                db_profile.efficiency_decay_rate = new_profile.efficiency_decay_rate
                db_profile.fatigue_factor = new_profile.fatigue_factor
                db_profile.recovery_factor = new_profile.recovery_factor
                db_profile.day_multipliers = new_profile.day_multipliers
                db_profile.soft_obligation_buffer = new_profile.soft_obligation_buffer
                db_profile.retention_rates = new_profile.retention_rates
                db_profile.last_updated = new_profile.last_updated
            else:
                # Create new record
                db_profile = ProductivityProfile(
                    student_id=student_id,
                    slot_weights=new_profile.slot_weights,
                    peak_windows=new_profile.peak_windows,
                    max_continuous_minutes=new_profile.max_continuous_minutes,
                    ideal_break_minutes=new_profile.ideal_break_minutes,
                    efficiency_decay_rate=new_profile.efficiency_decay_rate,
                    fatigue_factor=new_profile.fatigue_factor,
                    recovery_factor=new_profile.recovery_factor,
                    day_multipliers=new_profile.day_multipliers,
                    soft_obligation_buffer=new_profile.soft_obligation_buffer,
                    retention_rates=new_profile.retention_rates,
                    last_updated=new_profile.last_updated
                )
                self.db.add(db_profile)
                
            self.db.commit()
        
        return new_profile