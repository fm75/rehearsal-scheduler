from datetime import datetime, time, timedelta
from typing import List, Tuple

# We are assuming your parser and its data structures are in a sibling file
# called `temporal_parser`. If it's somewhere else, adjust the import.
from .temporal_parser import parse_temporal_expression, DayOfWeek

# A type alias makes the function signature much clearer.
Conflict = Tuple[datetime, datetime]

def find_conflicts_in_range(conflict_text: str, target_range: Tuple[datetime, datetime]) -> List[Conflict]:
    """
    Parses a natural language string for scheduling rules and finds all
    conflicting time slots within a given target datetime range.
    """
    # Step 1: Parse the text into structured rules.
    rules = parse_temporal_expression(conflict_text)
    
    found_conflicts: List[Conflict] = []
    target_start, target_end = target_range

    # Step 2: Iterate through each day in the target range.
    current_date = target_start.date()
    while current_date <= target_end.date():
        # For each day, check if any of our rules apply.
        for rule in rules:
            # This logic handles day-of-the-week rules, like "on Wednesdays"
            # Assumes your DayOfWeek enum matches Python's weekday() (Mon=0, Sun=6)
            if rule.day_of_week and rule.day_of_week.value == current_date.weekday():
                
                # For now, a simple day-of-week rule blocks the ENTIRE day.
                # We will make this more specific in the next TDD cycle.
                conflict_start_on_this_day = datetime.combine(current_date, time.min)
                conflict_end_on_this_day = datetime.combine(current_date, time.max)
                
                # Step 3: Calculate the actual overlap.
                overlap_start = max(target_start, conflict_start_on_this_day)
                overlap_end = min(target_end, conflict_end_on_this_day)
                
                # Step 4: If the overlap is valid, we found a conflict.
                if overlap_start < overlap_end:
                    found_conflicts.append((overlap_start, overlap_end))

        # Move to the next day.
        current_date += timedelta(days=1)
        
    return found_conflicts