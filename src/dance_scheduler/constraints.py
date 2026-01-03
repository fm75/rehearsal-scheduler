# dance_scheduler/constraints.py
"""
Defines the data structures for scheduling constraints.
"""
from dataclasses import dataclass

@dataclass
class DayOfWeekConstraint:
    """Represents a constraint for an entire day of the week."""
    day_of_week: str
    
    def __repr__(self) -> str:
        """
        Provides a developer-friendly string representation of the object.
        This is what you see when you print() the object or view it in a list.
        """
        return f"DayOfWeekConstraint(day_of_week='{self.day_of_week}')"

    def __eq__(self, other) -> bool:
        """
        Defines what it means for two DayOfWeekConstraint objects to be equal.
        They are equal if the 'other' object is also a DayOfWeekConstraint
        and their day_of_week attributes are the same.
        """
        if not isinstance(other, DayOfWeekConstraint):
            return NotImplemented
        return self.day_of_week == other.day_of_week


@dataclass
class TimeOnDayConstraint:
    """Represents a constraint for a specific time block on a given day."""
    day_of_week: str
    start_time: int  # Military time, e.g., 900 for 9:00 AM
    end_time: int    # Military time, e.g., 1700 for 5:00 PM

# You could also define a type alias for clarity
Constraint = DayOfWeekConstraint | TimeOnDayConstraint