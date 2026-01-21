"""
Time analysis domain logic.

Analyzes requested vs available rehearsal time.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TimeAnalysisResult:
    """Results from time analysis."""
    total_requested: float
    total_available: float
    deficit: float
    requests_by_director: Dict[str, Dict[str, Any]]
    venue_slots: List[Dict[str, Any]]
    missing_requests: List[str]
    
    @property
    def has_deficit(self) -> bool:
        """Check if there's insufficient time."""
        return self.deficit > 0
    
    @property
    def has_surplus(self) -> bool:
        """Check if there's extra time."""
        return self.deficit < 0
    
    @property
    def is_perfect_match(self) -> bool:
        """Check if requested equals available."""
        return self.deficit == 0
    
    @property
    def surplus(self) -> float:
        """Get surplus amount (positive number)."""
        return abs(self.deficit) if self.has_surplus else 0.0
    
    @property
    def utilization_pct(self) -> float:
        """Calculate venue utilization percentage."""
        if self.total_available == 0:
            return 0.0
        return (self.total_requested / self.total_available) * 100


class TimeAnalyzer:
    """Analyzes requested vs available rehearsal time."""
    
    def __init__(self, time_to_minutes_fn):
        """
        Initialize analyzer.
        
        Args:
            time_to_minutes_fn: Function to convert time to minutes
        """
        self.time_to_minutes = time_to_minutes_fn
    
    def analyze(
        self,
        time_requests: List[Dict[str, Any]],
        venue_schedule: List[Dict[str, Any]],
        use_allocated: bool = False
    ) -> TimeAnalysisResult:
        """
        Analyze requested vs available time.
        
        Args:
            time_requests: List of time request records
            venue_schedule: List of venue schedule records
            use_allocated: If True, use min_allocated column instead of min_requested
            
        Returns:
            TimeAnalysisResult with all analysis data
        """
        # Choose which column to use
        time_column = 'min_allocated' if use_allocated else 'min_requested'
        
        # Calculate total requested time
        total_requested = 0
        requests_by_director = {}
        missing_requests = []
        
        for row in time_requests:
            number_id = row.get('number_id', '')
            rhd_id = row.get('rhd_id', '')
            minutes_str = str(row.get(time_column, '')).strip()
            
            if minutes_str and minutes_str != '':
                try:
                    minutes = float(minutes_str)
                    total_requested += minutes
                    
                    if rhd_id not in requests_by_director:
                        requests_by_director[rhd_id] = {'total': 0, 'dances': []}
                    requests_by_director[rhd_id]['total'] += minutes
                    requests_by_director[rhd_id]['dances'].append({
                        'number_id': number_id,
                        'minutes': minutes
                    })
                except ValueError:
                    # Invalid minutes value - could log warning
                    pass
            else:
                missing_requests.append(number_id)
        
        # Calculate total available time
        total_available = 0
        venue_slots = []
        
        for row in venue_schedule:
            venue = row.get('venue', '')
            day = row.get('day', '')
            date = row.get('date', '')
            start_str = row.get('start', '')
            end_str = row.get('end', '')
            
            start_time = self._parse_time(start_str)
            end_time = self._parse_time(end_str)
            
            if start_time and end_time:
                # Calculate duration in minutes
                start_mins = self.time_to_minutes(start_time)
                end_mins = self.time_to_minutes(end_time)
                duration = end_mins - start_mins
                
                total_available += duration
                venue_slots.append({
                    'venue': venue,
                    'day': day,
                    'date': date,
                    'start': start_str,
                    'end': end_str,
                    'duration': duration
                })
        
        # Calculate deficit/surplus
        deficit = total_requested - total_available
        
        return TimeAnalysisResult(
            total_requested=total_requested,
            total_available=total_available,
            deficit=deficit,
            requests_by_director=requests_by_director,
            venue_slots=venue_slots,
            missing_requests=missing_requests
        )
    
    def _parse_time(self, time_str: str):
        """Parse time string to time object."""
        from rehearsal_scheduler.models.intervals import parse_time_string
        try:
            return parse_time_string(time_str)
        except Exception:
            return None