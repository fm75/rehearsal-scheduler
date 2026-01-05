# src/dance_scheduler/conflict_finder.py

from datetime import datetime, timedelta
from typing import List, Tuple

from .temporal_parser import parse_temporal_expression
from .scheduling_rule import DayOfWeek

# Maps Python's weekday() result (Monday=0) to our DayOfWeek enum
WEEKDAY_MAP = {
    0: DayOfWeek.MONDAY,
    1: DayOfWeek.TUESDAY,
    2: DayOfWeek.WEDNESDAY,
    3: DayOfWeek.THURSDAY,
    4: DayOfWeek.FRIDAY,
    5: DayOfWeek.SATURDAY,
    6: DayOfWeek.SUNDAY,
}


def find_conflicts_in_range(
    conflict_text: str, target_range: Tuple[datetime, datetime]
) -> List[Tuple[datetime, datetime]]:
    """
    Finds all conflicting time slots within a given date/time range based on a
    natural language text rule.
    """
    rules = parse_temporal_expression(conflict_text)
    conflicts = []
    
    start_date, end_date = target_range
    
    for rule in rules:
        for time_range in rule.time_ranges:
            # Iterate through each day in the target_range
            current_day = start_date
            while current_day <= end_date:
                day_of_week_enum = WEEKDAY_MAP[current_day.weekday()]

                # --- FIX 3: Handle rules that apply to ANY day ---
                # If rule.day_of_week is empty, it's a match for every day.
                # Otherwise, check if the current day is in the rule's specified days.
                is_day_match = not rule.day_of_week or day_of_week_enum in rule.day_of_week

                if is_day_match:
                    conflict_start = current_day.replace(
                        hour=time_range.start.hour,
                        minute=time_range.start.minute,
                        second=0,
                        microsecond=0,
                    )
                    conflict_end = current_day.replace(
                        hour=time_range.end.hour,
                        minute=time_range.end.minute,
                        second=0,
                        microsecond=0,
                    )
                    
                    # Ensure the conflict is within the overall target range before adding
                    if conflict_start < end_date and conflict_end > start_date:
                        overlap_start = max(conflict_start, start_date)
                        overlap_end = min(conflict_end, end_date)
                        if overlap_start < overlap_end:
                             conflicts.append((overlap_start, overlap_end))

                current_day += timedelta(days=1)
                
    return conflicts