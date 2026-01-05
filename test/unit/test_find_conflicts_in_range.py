# test_conflict_finder.py

import pytest
import datetime
from typing import List, Tuple, Optional
from rehearsal_scheduler.temporal_parser import DayOfWeek
from rehearsal_scheduler.conflict_finder import find_conflicts_in_range 


# --- Pytest Test Suite ---

# Define a target range for a full day of rehearsals
WED = (
    datetime.datetime(2025, 12, 10, 9, 0), # A Wednesday
    datetime.datetime(2025, 12, 10, 22, 0)
)

# Define a target range for a typical day
TUE_12_23 = (
    datetime.datetime(2025, 12, 23, 11, 0), # A Tuesday
    datetime.datetime(2025, 12, 23, 16, 0)
)

@pytest.mark.parametrize(
    "conflict_text, target_range, expected_output",
    [
        # =====================================================================
        # Group 1: Parsable text with NO conflict in the range
        # =====================================================================
        (
            "",
            WED, # Our target is a Wednesday
            [] # Correctly parsed, but no overlap -> empty list
        ),
        (
            None,
            WED, # Our target is a Wednesday
            [] # Correctly parsed, but no overlap -> empty list
        ),
        (
            "Tuesday",
            WED, # Our target is a Wednesday
            [] # Correctly parsed, but no overlap -> empty list
        ),
        (
            "Tu",
            WED, # Our target is a Wednesday
            [] # Correctly parsed, but no overlap -> empty list
        ),
        (
            "Unavailable on weekends",
            WED, # Our target is a Wednesday
            [] # Correctly parsed, but no overlap -> empty list
        ),
        (
            "Conflict on Dec 11, 2025",
            WED, # Our target is Dec 10
            [] # Specific date doesn't match
        ),
        (
            "Conflict on Dec 11",
            WED, # Our target is Dec 10
            [] # Specific date doesn't match
        ),
        (
            "Conflict on 12/11",
            WED, # Our target is Dec 10
            [] # Specific date doesn't match
        ),
        (
            "Not available 6am-8am on weekdays",
            WED, # Our target starts at 9am
            [] # Time range does not overlap
        ),

        # =====================================================================
        # Group 2: Parsable text WITH one or more conflicts in the range
        # =====================================================================
        (
            # The conflict completely contains the target
            "Not available on Wednesdays",
            (datetime.datetime(2025, 12, 10, 13, 0), datetime.datetime(2025, 12, 10, 15, 0)),
            [(datetime.datetime(2025, 12, 10, 13, 0), datetime.datetime(2025, 12, 10, 15, 0))]
        ),
        (
            # The conflict completely contains the target
            "Not available on Wednesdays",
            WED,
            [WED]
            # [(datetime.datetime(2025, 12, 10, 13, 0), datetime.datetime(2025, 12, 10, 15, 0))]
        ),
        (
            # The conflict completely contains the target
            "Conflict on Dec 9,10",
            WED, # Our target is Dec 10
            [WED]
        ),
        (
            # The conflict completely contains the target
            "Conflict on Dec 9, Dec 10",
            WED, # Our target is Dec 10
            [WED]
        ),
        (
            # The conflict completely contains the target
            "Conflict on Dec 10, Dec 11",
            WED, # Our target is Dec 10
            [WED]
        ),
        (
            # The conflict is partially overlapping at the start
            "Busy from 8am to 10am on Dec 10, 2025",
            WED, # Target day starts at 9am
            [(datetime.datetime(2025, 12, 10, 9, 0), datetime.datetime(2025, 12, 10, 10, 0))]
        ),
        (
            # Two distinct conflicts within the target day
            "Unavailable 10am-11am and 3pm-4pm on Dec 10, 2025",
            WED,
            [
                (datetime.datetime(2025, 12, 10, 10, 0), datetime.datetime(2025, 12, 10, 11, 0)),
                (datetime.datetime(2025, 12, 10, 15, 0), datetime.datetime(2025, 12, 10, 16, 0))
            ]
        ),

        # # =====================================================================
        # # Group 3: Ambiguous or Unparsable Text
        # # =====================================================================
        # (
        #     "Probably busy in the evening",
        #     TARGET_DAY,
        #     None # Ambiguous -> None
        # ),
        # (
        #     "Unavailable for the costume fitting",
        #     TARGET_DAY,
        #     None # Relative to unknown event -> None
        # ),
        # (
        #     "No.",
        #     TARGET_DAY,
        #     None # Not parsable -> None
        # ),
    ]
)
def test_find_conflicts_in_range(conflict_text, target_range, expected_output):
    """
    Tests the conflict finding function for specific overlaps.
    """
    assert find_conflicts_in_range(conflict_text, target_range) == expected_output


    @pytest.mark.parametrize("input_str, expected_day, expected_condition, expected_time", [
        ("tuesday after 2pm", DayOfWeek.TUESDAY, "after", datetime.time(14, 0)),
        # Let's add a few more to be thorough
        ("mo before 9am", DayOfWeek.MONDAY, "before", datetime.time(9, 0)),
        ("th until 12:30pm", DayOfWeek.THURSDAY, "until", datetime.time(12, 30)),
    ])
    def test_parses_day_with_explicit_time(self, input_str, expected_day, expected_condition, expected_time):
        """
        Tests parsing of strings that include a day, a condition, and an explicit time (am/pm or hh:mm).
        """
        parser = TemporalParser(input_str)
        
        # We'll need to decide what our parser's API looks like.
        # Maybe it has properties that get populated after parsing?
        assert parser.day_of_week == expected_day
        assert parser.condition == expected_condition
        assert parser.time == expected_time