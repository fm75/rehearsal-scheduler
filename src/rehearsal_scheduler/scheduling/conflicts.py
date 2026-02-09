"""Conflict detection logic for scheduling."""

from datetime import time
from typing import List, Tuple, Any, Dict, Optional
from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint, TimeOnDayConstraint,
    DateConstraint, DateRangeConstraint
)
from rehearsal_scheduler.models.intervals import TimeInterval, parse_date_string


def check_slot_conflicts(
    parsed_constraints: List[Tuple[str, Any]], 
    slot_day: str,
    slot_date: Optional[Any] = None,
    slot_start: Optional[time] = None,
    slot_end: Optional[time] = None
) -> List[str]:
    """
    Check if any constraints conflict with a time slot.
    
    Args:
        parsed_constraints: List of (token_text, parsed_result) tuples
        slot_day: Day of week (lowercase, e.g., "tuesday")
        slot_date: datetime.date object (optional)
        slot_start: Start time (optional)
        slot_end: End time (optional)
        
    Returns:
        List of conflicting constraint token texts (empty if no conflicts)
    """
    if not parsed_constraints:
        return []
    
    conflicting = []
    slot_day = slot_day.lower()
    
    for token_text, parsed_result in parsed_constraints:
        # Handle tuple of constraints
        if isinstance(parsed_result, tuple):
            constraint_list = parsed_result
        else:
            constraint_list = [parsed_result]
        
        for constraint in constraint_list:
            conflict = False
            
            if isinstance(constraint, DayOfWeekConstraint):
                # Unavailable all day on this day of week
                if constraint.day_of_week == slot_day:
                    conflict = True
            
            elif isinstance(constraint, TimeOnDayConstraint):
                # Unavailable during specific time on this day
                if constraint.day_of_week == slot_day and slot_start and slot_end:
                    constraint_start = time(constraint.start_time // 100, 
                                          constraint.start_time % 100)
                    constraint_end = time(constraint.end_time // 100, 
                                        constraint.end_time % 100)
                    
                    # Use TimeInterval.overlaps()
                    slot_interval = TimeInterval(slot_start, slot_end)
                    constraint_interval = TimeInterval(constraint_start, constraint_end)
                    if slot_interval.overlaps(constraint_interval):
                        conflict = True
            
            elif isinstance(constraint, DateConstraint):
                # Unavailable on specific date
                if slot_date and constraint.date == slot_date:
                    conflict = True
            
            elif isinstance(constraint, DateRangeConstraint):
                # Unavailable during date range
                if slot_date and constraint.start_date <= slot_date <= constraint.end_date:
                    conflict = True
            
            else:               # pragma: no cover
                pass
            
            if conflict:
                conflicting.append(token_text)
                break  # Don't add same token multiple times
    
    return conflicting


def check_slot_conflicts_from_dict(
    parsed_constraints: List[Tuple[str, Any]], 
    slot: Dict[str, str]
) -> List[str]:
    """
    Check if constraints conflict with a slot dictionary.
    
    Convenience wrapper that extracts slot params from a dict.
    
    Args:
        parsed_constraints: List of (token_text, parsed_result) tuples
        slot: Dictionary with 'day', 'date', 'start', 'end' keys
        
    Returns:
        List of conflicting constraint token texts
    """
    from rehearsal_scheduler.models.intervals import parse_time_string
    
    slot_day = slot['day'].lower()
    
    # Parse date
    try:
        slot_date = parse_date_string(slot['date'])
    except (ValueError, KeyError):
        slot_date = None
    
    # Parse times
    try:
        slot_start = parse_time_string(slot['start'])
        slot_end = parse_time_string(slot['end'])
    except (ValueError, KeyError):
        slot_start = None
        slot_end = None
    
    return check_slot_conflicts(
        parsed_constraints, slot_day, slot_date, slot_start, slot_end
    )