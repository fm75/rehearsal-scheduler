import pytest
from datetime import time

# Let's assume our parser code will live in a 'src' directory
# or a similarly structured package. Adjust the import path as needed.
from dance_scheduler.temporal_parser import TemporalParser, DayOfWeek

class TestDayWithExplicitTime:
    """
    Tests the TemporalParser's ability to handle strings containing a day,
    a condition, and an explicit time (e.g., '2pm', '9:30am').
    """
    
    @pytest.mark.parametrize("input_str, expected_day, expected_condition, expected_time", [
        # --- Standard PM cases ---
        ("tuesday after 2pm", DayOfWeek.TUESDAY, "after", time(14, 0)),
        ("w until 5pm", DayOfWeek.WEDNESDAY, "until", time(17, 0)),
        
        # --- Standard AM cases ---
        ("mo before 9am", DayOfWeek.MONDAY, "before", time(9, 0)),
        ("saturday on 11am", DayOfWeek.SATURDAY, "on", time(11, 0)),
        
        # --- Cases with minutes ---
        ("th until 12:30pm", DayOfWeek.THURSDAY, "until", time(12, 30)),
        ("f after 10:15am", DayOfWeek.FRIDAY, "after", time(10, 15)),
        
        # --- Edge case: Midnight and Noon ---
        ("sun before 12am", DayOfWeek.SUNDAY, "before", time(0, 0)), # Midnight
        ("mon after 12pm", DayOfWeek.MONDAY, "after", time(12, 0)),  # Noon
    ])

    
    def test_parses_day_with_explicit_time(self, input_str, expected_day, expected_condition, expected_time):
        """
        Tests parsing of strings that include a day, a condition, and an explicit time.
        """
        parser = TemporalParser(input_str)
        
        # These are the attributes we expect our parser to have after processing the string.
        assert parser.day_of_week == expected_day
        assert parser.condition == expected_condition
        assert parser.time == expected_time