# src/dance_scheduler/temporal_parser.py

import re
from datetime import time
from typing import List

from .scheduling_rule import DayOfWeek, SchedulingRule, TimeRange

# This map remains the same
DAY_MAP = {
    # Full names
    "monday": DayOfWeek.MONDAY,
    "tuesday": DayOfWeek.TUESDAY,
    "wednesday": DayOfWeek.WEDNESDAY,
    "thursday": DayOfWeek.THURSDAY,
    "friday": DayOfWeek.FRIDAY,
    "saturday": DayOfWeek.SATURDAY,
    "sunday": DayOfWeek.SUNDAY,
    # Common abbreviations
    "mon": DayOfWeek.MONDAY,
    "tue": DayOfWeek.TUESDAY,
    "tues": DayOfWeek.TUESDAY,
    "wed": DayOfWeek.WEDNESDAY,
    "thu": DayOfWeek.THURSDAY,
    "thur": DayOfWeek.THURSDAY,
    "thurs": DayOfWeek.THURSDAY,
    "fri": DayOfWeek.FRIDAY,
    "sat": DayOfWeek.SATURDAY,
    "sun": DayOfWeek.SUNDAY,
    # Single/Two-letter abbreviations
    "m": DayOfWeek.MONDAY,
    "t": DayOfWeek.TUESDAY,
    "w": DayOfWeek.WEDNESDAY,
    "th": DayOfWeek.THURSDAY,
    "f": DayOfWeek.FRIDAY,
    "sa": DayOfWeek.SATURDAY,
    "su": DayOfWeek.SUNDAY,
}

# This map for collective day terms is correct and stays
DAY_GROUP_MAP = {
    "weekends": {DayOfWeek.SATURDAY, DayOfWeek.SUNDAY},
    "weekend": {DayOfWeek.SATURDAY, DayOfWeek.SUNDAY},
    "weekdays": {
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    },
    "weekday": {
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    },
}

# --- FIX: Revert the regex to the version that produces 8 capturing groups ---
# The `(:(\d{2}))` part correctly creates two groups, one for the underscore to discard.
TIME_RANGE_REGEX = re.compile(
    r"(\d{1,2})(:(\d{2}))?\s*(am|pm)?\s*(?:-|to)\s*(\d{1,2})(:(\d{2}))?\s*(am|pm)", re.IGNORECASE
)


def _parse_time(hour_str, minute_str, am_pm_str):
    """Helper function to convert a parsed time string into a datetime.time object."""
    hour = int(hour_str)
    minute = int(minute_str) if minute_str else 0

    if am_pm_str and am_pm_str.lower() == "pm" and hour != 12:
        hour += 12
    elif am_pm_str and am_pm_str.lower() == "am" and hour == 12:
        hour = 0  # Midnight case

    return time(hour, minute)


def parse_temporal_expression(text: str) -> List[SchedulingRule]:
    """
    Parses a natural language string into a list of SchedulingRule objects.
    """
    if not text:
        return []

    is_unavailable = "unavailable" in text.lower() or "not available" in text.lower() or "busy" in text.lower()
    
    cleaned_text = re.sub(r'[,\.]', '', text.lower())
    words = cleaned_text.split()
    
    # This logic for finding days is correct and stays
    found_days = {DAY_MAP[word] for word in words if word in DAY_MAP}
    for word in words:
        if word in DAY_GROUP_MAP:
            found_days.update(DAY_GROUP_MAP[word])

    found_ranges = []
    for match in TIME_RANGE_REGEX.finditer(text):
        (
            start_hour, _, start_minute, start_am_pm,
            end_hour, _, end_minute, end_am_pm,
        ) = match.groups()

        if not start_am_pm:
            start_am_pm = end_am_pm

        start_time = _parse_time(start_hour, start_minute, start_am_pm)
        end_time = _parse_time(end_hour, end_minute, end_am_pm)
        found_ranges.append(TimeRange(start=start_time, end=end_time))

    if not found_ranges and (found_days or is_unavailable):
        all_day_range = TimeRange(start=time(0, 0), end=time(23, 59, 59))
        found_ranges.append(all_day_range)

    if not found_ranges:
        return []

    return [
        SchedulingRule(
            day_of_week=list(found_days),
            time_ranges=found_ranges,
            is_unavailable=is_unavailable,
            original_text=text,
        )
    ]