import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.reflected_models import SessionEvent, ContextSignal 
from typing import Dict, List, Tuple 
import datetime 
from app.schemas.behavior import SessionEventData, ContextSignalData

class FeatureExtractor:
    """
    Extracts features from session events and context signals for behavior analysis
    """

    def __init__(self, sessions: List[SessionEventData] = None, context_signals: List[ContextSignalData] = None):
        self.sessions = sessions or []
        self.context_signals = context_signals or []
    
    def extract_slot_efficiency(self, student_id: int, 
                                days_lookback: int = 30) -> Dict[str, float]:
        """
        Computes time slot efficiencies using Exponential Moving Average
        """
        # Filter sessions from the past days_lookback days 
        # Make sure cutoff_date is timezone-aware
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_lookback)
        filtered_sessions = [
            session for session in self.sessions
            if session.student_id == student_id
            and (session.start_time.replace(tzinfo=datetime.timezone.utc) if session.start_time.tzinfo is None else session.start_time) >= cutoff_date
            and session.completed == True
        ]

        # Process each session to extract time slot and efficiency
        slot_data = []
        for session in filtered_sessions:
            # Skip sessions with no end time
            if not session.end_time:
                continue 
            
            # Calculate efficiency metrics
            if not session.actual_duration or session.actual_duration <= 0 or not session.estimated_duration:
                continue  # Skip invalid durations
                
            efficiency = min(session.estimated_duration / session.actual_duration, 1.0)

            # Adjust by self rating if available
            if session.self_rating:
                efficiency *= (session.self_rating / 5.0)
            
            # Extract day of week and hour
            start_day = session.start_time.strftime("%A") # Monday, Tuesday, etc...
            start_hour = session.start_time.hour 

            # Create slot key (e.g. "Monday-14" for Monday 2PM)
            for hour in range(start_hour, start_hour + int((session.actual_duration or 0) / 60) + 1):
                slot_key = f"{start_day}-{hour}"
                slot_data.append((slot_key, efficiency))
            
        # Compute EMA for each slot
        slot_efficiencies = {}

        if slot_data:  # Only process if we have data
            df = pd.DataFrame(slot_data, columns=["slot", "efficiency"])
            for slot, entries in df.groupby("slot"):
                if not entries.empty:
                    # Compute EMA with alpha=0.3 (more weight to recent sessions)
                    ema = entries["efficiency"].ewm(alpha=0.3).mean().iloc[-1]
                    slot_efficiencies[slot] = round(ema, 2)

        return slot_efficiencies
    
    def identify_peak_windows(self, slot_efficiencies: Dict[str, float], 
                            threshold: float = 0.7) -> List[Dict]:
        """
        Identifies contiguous high-efficiency intervals
        """
        peak_windows = []

        # Group by day
        days = {}
        for slot, efficiency in slot_efficiencies.items():
            if efficiency >= threshold:
                day, hour = slot.split("-")
                if day not in days:
                    days[day] = []
                days[day].append((int(hour), efficiency))
        
        # Find contiguous windows for each day
        for day, hours in days.items():
            hours.sort(key=lambda x: x[0])

            current_window = []
            for hour, efficiency in hours:
                if not current_window or hour == current_window[-1][0] + 1:
                    current_window.append((hour, efficiency))
                else:
                    # Process the completed window if it has at least 2 hours
                    if len(current_window) >= 2:
                        avg_efficiency = sum(e for _, e in current_window) / len(current_window)
                        peak_windows.append({
                            "day": day,
                            "start_hour": current_window[0][0],
                            "end_hour": current_window[-1][0] + 1, # End hour is exclusive
                            "efficiency": round(avg_efficiency, 2)
                        })
                    # Start a new window
                    current_window = [(hour, efficiency)]
            
            if len(current_window) >= 2:
                avg_efficency = sum(e for _, e in current_window) / len(current_window)
                peak_windows.append({
                    "day": day,
                    "start_hour": current_window[0][0],
                    "end_hour": current_window[-1][0] + 1, # End hour is exclusive
                    "efficiency": round(avg_efficiency, 2)
                })
            
        return peak_windows 

    def compute_session_parameters(self, student_id: int) -> Dict[str, float]:
        """
        Calculates ideal session parameters based on past performance
        """
        # Filter completed sessions with ratings
        filtered_sessions = [
            session for session in self.sessions
            if session.student_id == student_id
            and session.completed == True
            and session.self_rating is not None
        ]
        # Sort by start_time descending and limit to 50
        filtered_sessions = sorted(filtered_sessions, key=lambda x: x.start_time, reverse=True)[:50]

        # Calculate parameters
        durations = [session.actual_duration for session in filtered_sessions if session.actual_duration]
        ratings = [session.self_rating for session in filtered_sessions if session.self_rating]

        parameters = {
            "max_continuous_minutes": 45, # Default
            "ideal_break_minutes": 10,    # Default
            "efficiency_decay_rate": 0.05 # Default
        }

        if durations and ratings:
            # Create a DataFrame to analyze relationship between duration and rating
            df = pd.DataFrame({
                "duration": durations,
                "rating": ratings
            })

            # Find the sweet spot - highest average rating by duration
            duration_rating = df.groupby(pd.cut(df["duration"], bins=range(0, 241, 15)), observed=True).mean()
            if not duration_rating.empty and not duration_rating["rating"].isna().all():
                best_idx = duration_rating["rating"].idxmax()
                if best_idx is not None and not pd.isna(best_idx):
                    if hasattr(best_idx, 'right'):
                        max_mins = best_idx.right
                        parameters["max_continuous_minutes"] = int(max_mins)
                    elif isinstance(best_idx, (int, float)):
                        parameters["max_continuous_minutes"] = int(min(best_idx, 90))


                    # Ideal break is proportional to session length (1:5 ratio)
                    parameters["ideal_break_minutes"] = int(max(max_mins / 5, 5))
            
            # Calculate efficiency decay rate
            if len(df) > 10:
                # Group by 15-minute increments beyond optimal time
                optimal = parameters["max_continuous_minutes"]
                df["beyond_optimal"] = df["duration"].apply(lambda x: max(0, x - optimal))
                decay_df = df.groupby(pd.cut(df["beyond_optimal"], bins=range(0, 121, 15))).mean()

                if len(decay_df) >= 2 and not decay_df["rating"].isna().all():
                    # Calculate slope of decay
                    x = np.array([i for i in range(len(decay_df))])
                    y = decay_df['rating'].fillna(method='ffill').fillna(method='bfill').values

                    if len(x) == len(y) and len(x) > 1:
                        slope, _ = np.polyfit(x, y, 1)
                        # Convert to a per-minute decay rate
                        parameters["efficiency_decay_rate"] = min(max(abs(slope) / 15, 0.01), 0.2)

        return parameters

    def compute_fatigue_recovery(self, student_id: int) -> Dict[str, float]:
        """
        Calculates fatigue and recovery parameters
        """
        # Filter completed sessions with ratings
        filtered_sessions = [
            session for session in self.sessions
            if session.student_id == student_id
            and session.completed == True
            and session.self_rating is not None
        ]
        # Sort by start_time
        filtered_sessions = sorted(filtered_sessions, key=lambda x: x.start_time)

        parameters = {
            "fatigue_factor": 0.15, # Default
            "recovery_factor": 0.2 # Default
        }

        if len(filtered_sessions) < 10:
            return parameters 
        
        # Calculate back-to-back sessions
        grouped_sessions = []
        current_group = []

        for i, session in enumerate(filtered_sessions):
            if i == 0:
                current_group.append(session)
                continue 
            
            prev_session = filtered_sessions[i - 1]
            # Skip if end_time is missing
            if not prev_session.end_time or not session.start_time:
                continue
            
            # If sessions are close (less than 30 minutes apart), consider them in the same group
            try:
                time_diff = (session.start_time - prev_session.end_time).total_seconds()
                if time_diff < 1800:  # 30 minutes in seconds
                    current_group.append(session)
                else:
                    if current_group:
                        grouped_sessions.append(current_group)
                    current_group = [session]
            except (TypeError, ValueError):
                # Handle any comparison errors
                continue
        
        if current_group:
            grouped_sessions.append(current_group)
        
        # Analyze rating trends within groups
        if grouped_sessions:
            # Calculate average rating for drop in a sequence
            drops = []
            for group in grouped_sessions:
                if len(group) > 1:
                    ratings = [s.self_rating for s in group if s.self_rating is not None]
                    if ratings and len(ratings) > 1:
                        # Calculate moving averagte to smooth out noise
                        ratings_series = pd.Series(ratings)
                        smooth_ratings = ratings_series.rolling(window=2, min_periods=1).mean()

                        # Calculate percentage drop from first to last
                        first_smooth = smooth_ratings.iloc[0]
                        last_smooth = smooth_ratings.iloc[-1]
                        if first_smooth > 0:
                            drop = (first_smooth - last_smooth) / first_smooth
                            drops.append(max(drop, 0)) # Only consider drops, not increases
            
            if drops:
                parameters["fatigue_factor"] = min(max(np.mean(drops), 0.05), 0.4)
    
        # Analyze recovery between groups
        recoveries = []
        for i in range(1, len(grouped_sessions)):
            prev_group = grouped_sessions[i - 1]
            curr_group = grouped_sessions[i]

            if prev_group and curr_group:
                prev_last = prev_group[-1]
                curr_first = curr_group[0]

                if prev_last.self_rating and curr_first.self_rating and prev_last.end_time and curr_first.start_time:
                    try:
                        # Calculate time gap in hours
                        time_gap = (curr_first.start_time - prev_last.end_time).total_seconds() / 3600

                        # Calculate rating improvement
                        if prev_last.self_rating > 0:
                            improvement = max(0, curr_first.self_rating - prev_last.self_rating) / prev_last.self_rating

                            # Normalize by time
                            recovery_rate = improvement / time_gap if time_gap > 0 else 0
                            recoveries.append(recovery_rate)
                    except (TypeError, ValueError):
                        # Handle any comparison errors
                        continue
        
        if recoveries:
            parameters["recovery_factor"] = min(max(np.mean(recoveries), 0.05), 0.5)
        
        return parameters

    def compute_adjustment_factors(self, student_id: int) -> Dict[str, Dict]:
        """
        Calculates day-of-week adjustment factors and other adjustments
        """
        # Filter completed sessions
        filtered_sessions = [
            session for session in self.sessions
            if session.student_id == student_id
            and session.completed == True
        ]

        # Default values
        defaults = {
            "day_multipliers": {
                'Monday': 1.0, 'Tuesday': 1.0, 'Wednesday': 1.0, 
                'Thursday': 1.0, 'Friday': 1.0, 'Saturday': 1.0, 'Sunday': 1.0
            },
            "soft_obligation_buffer": 30
        }

        if len(filtered_sessions) < 10:
            return defaults
        
        # Calculate day of week multipliers based on completion success and efficiency
        day_scores = {}
        day_counts = {}

        for session in filtered_sessions:
            day = session.start_time.strftime("%A")
            if day not in day_scores:
                day_scores[day] = 0
                day_counts[day] = 0

            # Calculate score based on completion, efficiency, and self-rating
            score = 0

            # Award points for completion
            if session.completed:
                score += 0.5
            
            # Add points for efficiency
            if session.actual_duration and session.estimated_duration and session.actual_duration > 0:
                efficiency = min(session.estimated_duration / session.actual_duration, 1.0)
                score += efficiency * 0.3
            
            # Add points for self-rating
            if session.self_rating:
                score += (session.self_rating / 5.0) * 0.2
            
            day_scores[day] += score
            day_counts[day] += 1
        
        # Calculate average score for each day
        day_multipliers = {}
        for day in day_scores:
            if day_counts[day] > 0:
                avg_score = day_scores[day] / day_counts[day]
                # Scale to reasonable multiplier (0.7 to 1.3)
                day_multipliers[day] = min(max(avg_score, 0.7), 1.3)
            else:
                day_multipliers[day] = 1.0
        
        # Normalize so average is 1.0
        if day_multipliers:
            avg_multiplier = sum(day_multipliers.values()) / len(day_multipliers)
            if avg_multiplier > 0:
                day_multipliers = {d: m / avg_multiplier for d, m in day_multipliers.items()}
        
        # Calculate buffer from context signals
        buffer_minutes = 30  # Default

        # Get buffer from early arrival versus calendar events
        if self.context_signals:
            # Filter calendar events for this student
            calendar_events = [signal for signal in self.context_signals 
                               if signal.student_id == student_id and 
                               signal.signal_type in ['class', 'meeting', 'exam']]
            
            # Get sessions that preceded calendar events
            early_buffers = []
            for event in calendar_events:
                for session in filtered_sessions:
                    # Skip if missing time data
                    if not session.end_time or not event.start_time:
                        continue
                        
                    try:
                        # If session ended before event started
                        if session.end_time < event.start_time:
                            buffer = (event.start_time - session.end_time).total_seconds() / 60
                            if buffer < 120:  # Only consider reasonable buffers
                                early_buffers.append(buffer)
                    except (TypeError, ValueError):
                        # Handle any comparison errors
                        continue
            
            if early_buffers:
                buffer_minutes = np.median(early_buffers)
        
        return {
            "day_multipliers": day_multipliers,
            "soft_obligation_buffer": max(min(buffer_minutes, 60), 10)  # Cap between 10-60 mins
        }

    def compute_retention_indicators(self, student_id: int) -> Dict[str, float]:
        """
        Analyzes optimal retention rates based on task repetition patterns
        """
        # This requires longitudinal data... for now return simple defaults
        retention_rates = {}
        
        # Default retention profile
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            for hour in range(7, 23):
                # Morning and evening tend to be better for retention
                if 8 <= hour <= 11:  # Morning
                    retention_rates[f"{day}-{hour}"] = 0.8
                elif 18 <= hour <= 21:  # Evening
                    retention_rates[f"{day}-{hour}"] = 0.7
                else:
                    retention_rates[f"{day}-{hour}"] = 0.6
        
        return retention_rates
    

    
