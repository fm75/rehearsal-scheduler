"""
Time and date interval models.

Provides core interval logic used throughout the scheduling system.
"""

from datetime import date, time, datetime
from dataclasses import dataclass
from typing import Optional

# Utility functions

def parse_time_string(time_str: str) -> time:
    """
    Parse a time string into a time object.
    
    Supports formats:
    - "9:00 AM", "5:00 PM" (12-hour with AM/PM)
    - "9 AM", "5 PM" (hour only with AM/PM)
    - "09:00", "17:00" (24-hour)
    - "09", "17" (hour only, 24-hour)
    
    Args:
        time_str: Time string to parse
        
    Returns:
        datetime.time object
        
    Raises:
        ValueError: If time string cannot be parsed
        
    Examples:
        >>> parse_time_string("9:00 AM")
        time(9, 0)
        >>> parse_time_string("17:00")
        time(17, 0)
    """
    time_str = time_str.strip()
    
    for fmt in ['%I:%M %p', '%I %p', '%H:%M', '%H']:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse time: {time_str}")


def parse_date_string(date_str: str) -> date:
    """
    Parse a date string into a date object.
    
    Supports formats:
    - "12/25/2025" (MM/DD/YYYY)
    - "12/25/25" (MM/DD/YY)
    
    Args:
        date_str: Date string to parse
        
    Returns:
        datetime.date object
        
    Raises:
        ValueError: If date string cannot be parsed
    """
    date_str = date_str.strip()
    
    for fmt in ['%m/%d/%Y', '%m/%d/%y']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse date: {date_str}")


def time_to_minutes(t: time) -> int:
    """
    Convert a time object to minutes since midnight.
    
    Args:
        t: datetime.time object
        
    Returns:
        Minutes since midnight (0-1439)
        
    Examples:
        >>> time_to_minutes(time(9, 30))
        570
    """
    return t.hour * 60 + t.minute

    
@dataclass(frozen=True)
class TimeInterval:
    """
    Represents a time range within a single day.
    
    Immutable to ensure thread safety and hashability.
    """
    start: time
    end: time
    
    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError(f"Start time {self.start} must be before end time {self.end}")
    
    def overlaps(self, other: 'TimeInterval') -> bool:
        """Check if this interval overlaps with another."""
        return self.start < other.end and other.start < self.end
    
    def contains_time(self, t: time) -> bool:
        """Check if a specific time falls within this interval."""
        return self.start <= t <= self.end
    
    def duration_minutes(self) -> int:
        """Calculate duration in minutes."""
        start_mins = self.start.hour * 60 + self.start.minute
        end_mins = self.end.hour * 60 + self.end.minute
        return end_mins - start_mins
    
    @classmethod
    def from_strings(cls, start_str: str, end_str: str) -> 'TimeInterval':
        """
        Create TimeInterval from time strings.
        
        Supports formats: "2:30 PM", "14:30"
        """
        return cls(parse_time_string(start_str), parse_time_string(end_str))


@dataclass(frozen=True)
class DateInterval:
    """
    Represents a single date or date range.
    
    For single dates, end_date is None.
    """
    start_date: date
    end_date: Optional[date] = None
    
    def __post_init__(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValueError(f"Start date {self.start_date} must be before end date {self.end_date}")
    
    def contains_date(self, d: date) -> bool:
        """Check if a date falls within this interval."""
        if self.end_date is None:
            return d == self.start_date
        return self.start_date <= d <= self.end_date
    
    def overlaps(self, other: 'DateInterval') -> bool:
        """Check if this date range overlaps with another."""
        end = self.end_date or self.start_date
        other_end = other.end_date or other.start_date
        return self.start_date <= other_end and other.start_date <= end
    
    def duration_days(self) -> int:
        """Calculate duration in days (inclusive)."""
        if self.end_date is None:
            return 1
        return (self.end_date - self.start_date).days + 1
    
    def is_single_date(self) -> bool:
        """Check if this is a single date (not a range)."""
        return self.end_date is None


@dataclass
class VenueSlot:
    """
    Represents a scheduled venue time slot.
    
    Combines location, date, and time information.
    """
    venue: str
    day_of_week: str  # lowercase: "monday", "tuesday", etc.
    date: date
    time_interval: TimeInterval
    available_minutes: int = 0  # Set from time_interval if None
    remaining_minutes: int = 0  # Tracks scheduling, set to available_minutes if None
    
    def __post_init__(self):
        self.day_of_week = self.day_of_week.lower()
        
        if self.available_minutes == 0:             # pragma: no branch
            self.available_minutes = self.time_interval.duration_minutes()
        
        if self.remaining_minutes == 0:             # pragma: no branch
            self.remaining_minutes = self.available_minutes
    
    def matches_day(self, day_of_week: str) -> bool:
        """Check if this slot is on the given day of week."""
        return self.day_of_week == day_of_week.lower()
    
    def can_fit(self, minutes: int) -> bool:
        """Check if the given duration fits in remaining time."""
        return self.remaining_minutes >= minutes
    
    def allocate(self, minutes: int) -> bool:
        """
        Allocate time from this slot.
        
        Returns True if successful, False if insufficient time.
        """
        if self.can_fit(minutes):
            object.__setattr__(self, 'remaining_minutes', self.remaining_minutes - minutes)
            return True
        return False