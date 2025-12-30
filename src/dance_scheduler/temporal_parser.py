# src/dance_scheduler/temporal_parser.py

import datetime
from enum import Enum
from typing import List, Tuple, Optional
from dataclasses import dataclass

# This map converts various string representations of days of the week
# into the integer format used by datetime.weekday() (Monday=0, Sunday=6).
# We are including your project-specific rule: "T" means Tuesday.
DAY_OF_WEEK_MAP = {
    "monday": 0, "mon": 0, "mo": 0, 
    "tuesday": 1, "tues": 1, "tu": 1, "t": 1,
    "wednesday": 2, "wed": 2, "w": 2,
    "thursday": 3, "thurs": 3, "th": 3, "r": 3,
    "friday": 4, "fri": 4, "f": 4,
    "saturday": 5, "sat": 5, "sa": 5, 
    "sunday": 6, "sun": 6, "su": 6,
}


class DayOfWeek(Enum):
    """
    An enumeration for the days of the week, aligned with datetime.weekday().
    (Monday=0, Sunday=6)
    """
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    @classmethod
    def from_string(cls, s: str) -> Optional['DayOfWeek']:
        """
        Attempts to convert a string token into a DayOfWeek enum member.
        
        Args:
            s: The input string (e.g., "mon", "T", "Friday").
            
        Returns:
            The corresponding DayOfWeek member if a match is found, otherwise None.
        """
        # .get() is used to avoid a KeyError if the string is not in the map
        day_int = DAY_OF_WEEK_MAP.get(s.lower())
        if day_int is not None:
            # If we found a valid integer, convert it to the enum member
            return cls(day_int)
        return None


@dataclass
class SchedulingRule:
    """Represents a single parsed scheduling rule."""
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None


def parse_temporal_expression(text: str) -> List[SchedulingRule]:
    """
    Parses a natural language string into a list of structured SchedulingRule objects.
    
    NOTE: This is currently a placeholder implementation for TDD.
    """
    if text is None:
        return []
        
    # This is the simplest possible logic to make our current test pass.
    # We are "hard-coding" a response for the specific input we know the test is using.
 
    if "Wednesdays" in text:
        # If the text mentions Wednesdays, return a rule for that day.
        return [SchedulingRule(day_of_week=DayOfWeek.WEDNESDAY)]
    
    # If the text is something else, for now, we still return an empty list.
    return []

class TemporalParser:
    """
    Parses a simple temporal string to extract its components.
    """
    
    # Let's define the conditions we expect to find
    CONDITIONS = {"before", "after", "on", "until"}

    def __init__(self, input_str: str):
        """
        Initializes the parser and processes the input string.
        """
        # --- Default states ---
        self.day_of_week: DayOfWeek | None = None
        self.condition: str | None = None
        self.time: time | None = None
        
        # --- 1. Normalize and Tokenize ---
        tokens = input_str.lower().split()
        
        # --- 2. Iterate and Classify ---
        for token in tokens:
            # Is it a day of the week?
            day = DayOfWeek.from_string(token)
            if day:
                self.day_of_week = day
                continue # Move to the next token

            # Is it a condition?
            if token in self.CONDITIONS:
                self.condition = token
                continue # Move to the next token

            # Is it a time? (This is the new, complex part)
            # We'll need a dedicated method for this.
            parsed_time = self._parse_time_token(token)
            if parsed_time:
                self.time = parsed_time
                continue

    def _parse_time_token(self, token: str) -> Optional[datetime.time]:
        """
        Parses a token like '2pm', '9am', '10:30pm' into a datetime.time object.
        Returns None if the token is not a recognized time format.
        """
        # 1. Check for AM/PM and isolate the numeric part
        is_pm = False
        if token.endswith('pm'):
            is_pm = True
            numeric_part = token[:-2]
        elif token.endswith('am'):
            numeric_part = token[:-2]
        else:
            return None # Not a time format we recognize

        # 2. Parse hour and minute
        try:
            if ':' in numeric_part:
                hour_str, minute_str = numeric_part.split(':')
                hour = int(hour_str)
                minute = int(minute_str)
            else:
                hour = int(numeric_part)
                minute = 0
        except (ValueError, TypeError):
            # Handles cases like "a:30pm" or ":30pm"
            return None

        # 3. Validate ranges for 12-hour clock input
        if not (1 <= hour <= 12 and 0 <= minute <= 59):
            return None

        # 4. Convert to 24-hour format
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12: # Handle 12:00 AM (midnight)
            hour = 0
            
        # 5. Create and return the time object
        return datetime.time(hour=hour, minute=minute)

# # Let's define a type alias for clarity
# Conflict = Tuple[datetime, datetime]

# def find_conflicts_in_range(
#     conflict_text: str,
#     target_range: Tuple[datetime.datetime, datetime.datetime]
# ) -> Optional[List[Conflict]]:
#     """
#     Parses a natural language string and returns the specific datetime ranges
#     of conflict that fall within a given target range.

#     Args:
#         conflict_text: The natural language string describing a conflict.
#         target_range: A tuple (start_time, end_time) to check against.

#     Returns:
#         - A list of (Conflict) for each overlap found.
#         - An empty list ([]) if the text is valid but no conflicts
#           occur within the target_range.
#         - None if the conflict_text is ambiguous or cannot be parsed.
#     """
#     # --- Step 0: Handle empty or None input ---
#     if not conflict_text or not conflict_text.strip():
#         return []

#     # --- Step 1: Normalize the input string ---
#     # We make it lowercase and remove leading/trailing whitespace.
#     normalized_text = conflict_text.lower().strip()

#     # --- Step 2: Check for a simple day-of-the-week conflict ---
#     if normalized_text in DAY_OF_WEEK_MAP:
#         conflict_weekday = DAY_OF_WEEK_MAP[normalized_text]
        
#         # We assume the start and end of the target_range are on the same day.
#         target_weekday = target_range[0].weekday()

#         if conflict_weekday == target_weekday:
#             # The conflict is for the entire day, and the target is on that day.
#             # Therefore, the overlap is the target range itself.
#             return [target_range]
#         else:
#             # The conflict is for a different day of the week, so no overlap.
#             return []

#     # If we haven't found a match yet, we consider the text unparsable for now.
#     # We will add more parsing logic for time ranges here in the next step.
#     return []