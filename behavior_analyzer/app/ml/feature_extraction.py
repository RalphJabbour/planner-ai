import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.session import SessionEvent, ContextSignal 
from typing import Dict, List, Tuple 
import datetime 

class FeatureExtractor:
    """
    Extracts features from session events and context signals for behavior analysis
    """

    def __init__(self, db: Session):
        self.db = db 
    
    def extract_slot_efficiency(self, student_id: int, 
                                days_lookback: int = 30) -> Dict[str, float]:
        """
        Computes time slot efficiencies using Exponential Moving Average
        """
        # Get sessions from the past days_lookback days 
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_lookback)
        sessions = self.db.query(SessionEvent).filter(
            SessionEvent.student_id == student_id,
            SessionEvent.start_time >= cutoff_date,
            SessionEvent.completed == True
        ).all()

        # Process each session to extract time slot and efficiency
        slot_data = []
        for session in sessions:
            # Skip sessions with no end time
            if not session.end_time:
                continue 
            
            # Calculate efficiency metrics
            efficiency = min(session.estimated_duration / session.actual_duration, 1.0) if session.actual_duration else 0

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

        for slot, entries in pd.DataFrame(slot_data, columns=["slot", "efficiency"]).groupby("slot"):
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

    def compute_session_paramters(self, student_id: int) -> Dict[str, float]:
        """
        Calculates ideal session parameters based on past performance
        """
        # Get completed sessions with ratings
        sessions = self.db.query(SessionEvent).filter(
            SessionEvent.student_id == student_id,
            SessionEvent.completed == True,
            SessionEvent.self_rating != None
        ).order_by(SessionEvent.start_time.desc()).limit(50).all()

        # Calculate parameters
        durations = [session.actual_duration for session in sessions if session.actual_duration]
        ratings = [session.self_rating for session in sessions if session.self_rating]

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
            duration_rating = df.groupby(pd.cut(df["duration"], bins=range(0, 241, 15))).mean()
            if not duration_rating.empty:
                best_idx = duration_rating["rating"].idxmax()
                if best_idx:
                    # Extract the upper bound of the interval
                    max_mins = best_idx.right
                    parameters["max_continuous_minutes"] = int(max_mins)


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
        # Get all completed sessions ordered by time
        sessions = self.db.query(SessionEvent).filter(
            SessionEvent.student_id == student_id,
            SessionEvent.completed == True,
            SessionEvent.self_rating != None
        ).order_by(SessionEvent.start_time).all()

        parameters = {
            "fatigue_factor": 0.15, # Default
            "recovery_factor": 0.2 # Default
        }

        if len(sessions) < 10:
            return parameters 
        
        # Calculate back-to-back sessions
        grouped_sessions = []
        current_group = []

        for i, session in enumerate(sessions):
            if i == 0:
                current_group.append(session)
                continue 
            
            prev_session = sessions[i - 1]
            # If sessions are close (less than 30 minutes apart), consider them in the same group
            if (session.start_time - prev_session.end_time).total_seconds() < 1800:
                current_group.append(session)
            else:
                if current_group:
                    grouped_sessions.append(current_group)
                current_group = [session]
        
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

                if prev_last.self_rating and curr_first.self_rating:
                    # Calculate time gap in hours
                    time_gap = (curr_first.start_time - prev_last.end_time).total_seconds() / 3600

                    # Calculate rating improvement
                    if prev_last.self_rating > 0:
                        improvement = max(0, curr_first.self_rating - prev_last.self_rating) / prev_last.self_rating

                        # Normalize by time
                        recovery_rate = improvement / time_gap if time_gap > 0 else 0
                        recoveries.append(recovery_rate)

        if recoveries:
            # Take the median to avoid outliers
            parameters["recovery_factor"] = min(max(np.median(recoveries), 0.05), 0.5)
        
        return parameters

    def compute_adjustment_factors(self, student_id: int) -> Dict[str, Dict]:
        """
        Calculates day-of-week multipliers and another adjustment factors
        """

        # Get all completed sessions with ratings
        sessions = self.db.query(SessionEvent).filter(
            SessionEvent.student_id == student_id,
            SessionEvent.completed == True,
            SessionEvent.self_rating != None
        ).all()

        # Default values - neutral multiplier
        default_days = {
            'Monday': 1.0, 'Tuesday': 1.0, 'Wednesday': 1.0, 
            'Thursday': 1.0, 'Friday': 1.0, 'Saturday': 1.0, 'Sunday': 1.0 
        }

        if len(sessions) < 7: # Need at least a week's worth of data
            return {"day_multipliers": default_days, "soft_obligation_buffer": 30}
        
        # Group by day of week
        day_ratings = {}
        for session in sessions:
            day = session.start_time.strftime("%A")
            if day not in day_ratings:
                day_ratings[day] = []
            if session.self_rating:
                day_ratings[day].append(session.self_rating)
        
        # Calculate average rating by day
        day_averages = {}
        for day, ratings in day_ratings.items():
            if ratings:
                day_averages[day] = sum(ratings) / len(ratings)

        # Skip calculation if we don't have enough days
        if len(day_averages) < 3:
            return {"day_multipliers": default_days, "soft_obligation_buffer": 30}

        # Calculate overall average
        overall_avg = sum(day_averages.values()) / len(day_averages)

        # Calculate multipliers relative to overall average
        day_multipliers = {}
        for day in default_days:
            if day in day_averages and overall_avg > 0:
                # Normalize around 1.0 with limited range (0.8 to 1.2)
                multiplier = day_averages[day] / overall_avg
                day_multipliers[day] = min(max(multiplier, 1.2), 0.8)
            else:
                day_multipliers[day] = 1.0
        
        # Calculate soft obligation buffer based on context analysis
        buffer = 30 # Default 30 minutes

        # Get context signals
        context_signals = self.db.query(ContextSignal).filter(
            ContextSignal.student_id == student_id,
        ).all()

        # Look for patterns in session performance around context events
        if context_signals and sessions:
            pre_scores = []
            post_scores = []

            for signal in context_signals:
                # Find sessions within 2 hours before and after this context event
                pre_event = [s for s in sessions if signal.start_time - datetime.timedelta(hours=2) <= s.end_time <= signal.start_time]
                post_event = [s for s in sessions if signal.end_time <= s.start_time <= signal.end_time + datetime.timedelta(hours=2)]

                # Calculate average ratings
                if pre_event and any(s.self_rating for s in pre_event):
                    pre_scores.append(sum(s.self_rating for s in pre_event if s.self_rating) / sum(1 for s in pre_event if s. self_rating))

                if post_event and any(s.self_rating for s in post_event):
                    post_scores.append(sum(s.self_rating for s in post_event if s.self_rating) / sum(1 for s in post_event if s.self_rating))
            
            # Calculate buffer based on performance drop
            if pre_scores and post_scores:
                pre_avg = sum(pre_scores) / len(pre_scores)
                post_avg = sum(post_scores) / len(post_scores)
            
                # If post-event performance is lower, increase buffer
                if post_avg < pre_avg:
                    drop_ratio = max(0, (pre_avg - post_avg) / pre_avg)
                    # Scale buffer: 15-60 minutes based on drop
                    buffer = min(max(15 + drop_ratio * 45, 15), 60)

        return {
            "day_multipliers": day_multipliers,
            "soft_obligation_buffer": buffer
        }

    def compute_retention_indicators(self, student_id: int) -> Dict[str, float]:
        """
        Caclulates retention rates by time slot (optional)
        """
        # This would require quiz/test data which may not be available
        # For now, return a placeholder with reasonable defaults

        # Get time slots from efficiency data
        slot_efficiencies = self.extract_slot_efficiency(student_id)

        # Generate simulated retention data based on slot efficiency
        # The assumption: higher efficiency slots correlate with better retention
        retention_rates = {}

        for slot, efficiency in slot_efficiencies.items():
            # Add some randomness but keep correlation with efficiency
            noise = np.random.uniform(0, 0.1)
            retention = min(max(efficiency * 0.8 + noise, 0.3), 0.95)
            retention_rates[slot] = round(retention, 2)
        
        return retention_rates
    

    
