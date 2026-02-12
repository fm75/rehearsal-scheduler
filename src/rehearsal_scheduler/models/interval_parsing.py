"""
Interval Parsing Utilities

Utilities for parsing formatted time interval strings back into TimeInterval objects.
Used by the scheduler to work with availability windows.
"""

from datetime import time
from typing import List
import re

from rehearsal_scheduler.models.intervals import TimeInterval


def parse_time_string(time_str: str) -> time:
    """
    Parse a formatted time string to a time object.
    
    Handles formats like:
    - "7:00 pm"
    - "11:30 am"
    - "12:00 pm" (noon)
    - "12:00 am" (midnight)
    
    Args:
        time_str: Formatted time string
        
    Returns:
        time object
        
    Raises:
        ValueError: If string cannot be parsed
        
    Examples:
        >>> parse_time_string("7:00 pm")
        time(19, 0)
        >>> parse_time_string("11:30 am")
        time(11, 30)
    """
    time_str = time_str.strip().lower()
    
    # Match patterns like "7:00 pm" or "11:30 am"
    match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', time_str)
    
    if not match:
        raise ValueError(f"Cannot parse time string: {time_str}")
    
    hours = int(match.group(1))
    minutes = int(match.group(2))
    meridiem = match.group(3)
    
    # Convert to 24-hour format
    if meridiem == 'am':
        if hours == 12:
            hours = 0  # 12:00 am = midnight
    else:  # pm
        if hours != 12:
            hours += 12  # Convert to 24-hour (but 12 pm stays 12)
    
    return time(hours, minutes)


def parse_interval_string(interval_str: str) -> TimeInterval:
    """
    Parse a single interval string to TimeInterval.
    
    Handles format: "7:00 pm - 8:30 pm"
    
    Args:
        interval_str: Formatted interval string
        
    Returns:
        TimeInterval object
        
    Raises:
        ValueError: If string cannot be parsed
        
    Examples:
        >>> parse_interval_string("7:00 pm - 8:30 pm")
        TimeInterval(start=time(19, 0), end=time(20, 30))
    """
    interval_str = interval_str.strip()
    
    # Split on " - " (with spaces)
    parts = interval_str.split(' - ')
    
    if len(parts) != 2:
        raise ValueError(f"Invalid interval format: {interval_str}")
    
    start_time = parse_time_string(parts[0])
    end_time = parse_time_string(parts[1])
    
    return TimeInterval(start_time, end_time)


def parse_availability_string(availability_str: str) -> List[TimeInterval]:
    """
    Parse comma-separated interval strings to list of TimeIntervals.
    
    Handles formats like:
    - "7:00 pm - 8:30 pm"
    - "7:00 pm - 8:30 pm, 9:00 pm - 9:30 pm"
    - "" (empty string)
    
    Args:
        availability_str: Formatted availability string (possibly comma-separated)
        
    Returns:
        List of TimeInterval objects (empty list if no availability)
        
    Examples:
        >>> parse_availability_string("7:00 pm - 8:30 pm")
        [TimeInterval(start=time(19, 0), end=time(20, 30))]
        
        >>> parse_availability_string("7:00 pm - 8:00 pm, 9:00 pm - 9:30 pm")
        [TimeInterval(...), TimeInterval(...)]
        
        >>> parse_availability_string("")
        []
    """
    if not availability_str or availability_str.strip() == '':
        return []
    
    # Split on comma
    interval_strings = availability_str.split(',')
    
    intervals = []
    for interval_str in interval_strings:
        interval_str = interval_str.strip()
        if interval_str:
            intervals.append(parse_interval_string(interval_str))
    
    return intervals


def does_duration_fit_in_intervals(
    duration_minutes: int,
    available_intervals: List[TimeInterval]
) -> bool:
    """
    Check if a duration can fit within any of the available intervals.
    
    Args:
        duration_minutes: Required duration in minutes
        available_intervals: List of available time windows
        
    Returns:
        True if duration fits in at least one interval
        
    Examples:
        >>> intervals = [TimeInterval(time(19, 0), time(20, 30))]  # 90 minutes
        >>> does_duration_fit_in_intervals(60, intervals)
        True
        >>> does_duration_fit_in_intervals(120, intervals)
        False
    """
    for interval in available_intervals:
        interval_duration = interval.duration_minutes()
        if interval_duration >= duration_minutes:
            return True
    
    return False


def find_best_fit_interval(
    duration_minutes: int,
    available_intervals: List[TimeInterval]
) -> TimeInterval:
    """
    Find the best-fitting interval for a given duration.
    
    Returns the smallest interval that can accommodate the duration.
    This is a "best fit" bin packing strategy.
    
    Args:
        duration_minutes: Required duration in minutes
        available_intervals: List of available time windows
        
    Returns:
        Best-fitting TimeInterval
        
    Raises:
        ValueError: If no interval is large enough
        
    Examples:
        >>> intervals = [
        ...     TimeInterval(time(19, 0), time(21, 0)),  # 120 minutes
        ...     TimeInterval(time(14, 0), time(15, 30))  # 90 minutes
        ... ]
        >>> find_best_fit_interval(60, intervals)
        TimeInterval(start=time(14, 0), end=time(15, 30))  # Smallest that fits
    """
    # Filter to intervals that can fit the duration
    candidates = [
        iv for iv in available_intervals 
        if iv.duration_minutes() >= duration_minutes
    ]
    
    if not candidates:
        raise ValueError(f"No interval large enough for {duration_minutes} minutes")
    
    # Return smallest candidate (best fit)
    return min(candidates, key=lambda iv: iv.duration_minutes())