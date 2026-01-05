from dataclasses import dataclass
from datetime import time
from enum import Enum, auto
from typing import List


class DayOfWeek(Enum):
    MONDAY = auto()
    TUESDAY = auto()
    WEDNESDAY = auto()
    THURSDAY = auto()
    FRIDAY = auto()
    SATURDAY = auto()
    SUNDAY = auto()


@dataclass(frozen=True)
class TimeRange:
    """Represents a range of time with a start and end."""
    start: time
    end: time


@dataclass(frozen=True)
class SchedulingRule:
    """
    Represents a rule for scheduling, e.g., "Unavailable on Mondays 9am-11am".
    """
    day_of_week: List[DayOfWeek]
    time_ranges: List[TimeRange]
    is_unavailable: bool
    original_text: str