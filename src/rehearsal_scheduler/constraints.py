# dance_scheduler/constraints.py
"""
Defines the data structures for scheduling constraints.
"""
from datetime import date
from dataclasses import dataclass
from typing import TypeAlias

TimeInterval: TypeAlias = tuple[int, int]

@dataclass(frozen=True)
class DayOfWeekConstraint:
    """Represents a constraint for an entire day of the week."""
    day_of_week: str

    # def get_conflicting_intervals(self, slot: RehearsalSlot) -> list[TimeInterval]:
    #     if self.day_of_week == slot.day_of_week:
    #         return [(slot.start_time, slot.end_time)]
    #     return []

    def __repr__(self) -> str:
        """
        Provides a developer-friendly string representation of the object.
        This is what you see when you print() the object or view it in a list.
        """
        return f"DayOfWeekConstraint(day_of_week='{self.day_of_week}')"

    # def __eq__(self, other) -> bool:
    #     """
    #     Defines what it means for two DayOfWeekConstraint objects to be equal.
    #     They are equal if the 'other' object is also a DayOfWeekConstraint
    #     and their day_of_week attributes are the same.
    #     """
    #     if not isinstance(other, DayOfWeekConstraint):
    #         return NotImplemented
    #     return self.day_of_week == other.day_of_week


@dataclass(frozen=True)
class TimeOnDayConstraint:
    """Represents a constraint for a specific time block on a given day."""
    day_of_week: str
    start_time: int  # Military time, e.g., 900 for 9:00 AM
    end_time: int    # Military time, e.g., 1700 for 5:00 PM

    # def get_conflicting_intervals(self, slot: RehearsalSlot) -> list[TimeInterval]:
    #     """
    #     Checks for conflicts if the day matches AND the time intervals overlap.
    #     """
    #     if self.day_of_week != slot.day_of_week:
    #         return [] # No conflict if it's not on the right day.

    #     # Classic interval overlap check: max(starts) < min(ends)
    #     overlap_start = max(self.start_time, slot.start_time)
    #     overlap_end = min(self.end_time, slot.end_time)

    #     if overlap_start < overlap_end:
    #         # A conflict exists! Return the actual interval of the conflict.
    #         return [(overlap_start, overlap_end)]
        
    #     return []


class DateConstraint:
    """Represents unavailability on a specific date."""
    
    def __init__(self, date: date):
        self.date = date
    
    def __repr__(self):
        return f"DateConstraint(date={self.date})"
    
    def __eq__(self, other):
        return isinstance(other, DateConstraint) and self.date == other.date


class DateRangeConstraint:
    """Represents unavailability over a date range."""
    
    def __init__(self, start_date: date, end_date: date):
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
        self.start_date = start_date
        self.end_date = end_date
    
    def __repr__(self):
        return f"DateRangeConstraint(start={self.start_date}, end={self.end_date})"
    
    def __eq__(self, other):
        return (isinstance(other, DateRangeConstraint) and 
                self.start_date == other.start_date and 
                self.end_date == other.end_date)

        
# You could also define a type alias for clarity
Constraint = DayOfWeekConstraint | TimeOnDayConstraint | DateConstraint | DateRangeConstraint


@dataclass(frozen=True)
class RehearsalSlot:
    """Represents a single, structured rehearsal event."""
    rehearsal_date: date
    day_of_week: str  # Standardized, lowercase e.g., 'wednesday'
    start_time: int   # Military time, e.g., 1100
    end_time: int     # Military time, e.g., 1200