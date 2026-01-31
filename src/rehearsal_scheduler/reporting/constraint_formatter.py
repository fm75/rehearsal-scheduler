"""
Utility functions for formatting constraints in human-readable form.
"""

from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint,
    DateConstraint,
    DateRangeConstraint,
    TimeOnDateConstraint
)


def format_time(military_time: int) -> str:
    """
    Format military time as human-readable string.
    
    Args:
        military_time: Time as integer (e.g., 1730 for 5:30 PM)
        
    Returns:
        Formatted string (e.g., "5:30 pm")
    """
    hours = military_time // 100
    minutes = military_time % 100
    
    # Convert to 12-hour format
    if hours == 0:
        return f"12:{minutes:02d} am"
    elif hours < 12:
        return f"{hours}:{minutes:02d} am"
    elif hours == 12:
        return f"12:{minutes:02d} pm"
    else:
        return f"{hours - 12}:{minutes:02d} pm"


def format_constraint(constraint) -> str:
    """
    Format a constraint object as human-readable text.
    
    Args:
        constraint: Any constraint type
        
    Returns:
        Human-readable description
    """
    if isinstance(constraint, DayOfWeekConstraint):
        return constraint.day_of_week.title()
    
    elif isinstance(constraint, TimeOnDayConstraint):
        day = constraint.day_of_week.title()
        
        # Handle "all day" case (0 to 2359)
        if constraint.start_time == 0 and constraint.end_time >= 2359:
            return day
        
        # Handle "before" case (0 to specific time)
        if constraint.start_time == 0:
            return f"{day} before {format_time(constraint.end_time)}"
        
        # Handle "after" case (specific time to end of day)
        if constraint.end_time >= 2359:
            return f"{day} after {format_time(constraint.start_time)}"
        
        # Handle time range
        return f"{day} {format_time(constraint.start_time)}-{format_time(constraint.end_time)}"
    
    elif isinstance(constraint, DateConstraint):
        return constraint.date.strftime("%b %d, %Y")
    
    elif isinstance(constraint, DateRangeConstraint):
        start = constraint.start_date.strftime("%b %d")
        end = constraint.end_date.strftime("%b %d, %Y")
        return f"{start} - {end}"
    
    elif isinstance(constraint, TimeOnDateConstraint):
        date_str = constraint.date.strftime("%b %d, %Y")
        
        # Handle "all day"
        if constraint.start_time == 0 and constraint.end_time >= 2359:
            return date_str
        
        # Handle "before"
        if constraint.start_time == 0:
            return f"{date_str} before {format_time(constraint.end_time)}"
        
        # Handle "after"
        if constraint.end_time >= 2359:
            return f"{date_str} after {format_time(constraint.start_time)}"
        
        # Handle time range
        return f"{date_str} {format_time(constraint.start_time)}-{format_time(constraint.end_time)}"
    
    else:
        # Fallback to string representation
        return str(constraint)