"""
Unit tests for parse_time_to_military function.

Tests all supported time formats and edge cases.
"""

import pytest
from rehearsal_scheduler.models.intervals import parse_time_to_military


class TestParseTimeToMilitary:
    """Test parse_time_to_military function with various input formats."""
    
    def test_integer_passthrough(self):
        """Test that integer military time passes through unchanged."""
        assert parse_time_to_military(1800) == 1800
        assert parse_time_to_military(0) == 0
        assert parse_time_to_military(2359) == 2359
        assert parse_time_to_military(1200) == 1200
    
    def test_twelve_hour_am_format(self):
        """Test parsing 12-hour AM format."""
        assert parse_time_to_military("6:00 AM") == 600
        assert parse_time_to_military("11:30 AM") == 1130
        assert parse_time_to_military("12:00 AM") == 0  # Midnight
        assert parse_time_to_military("12:30 AM") == 30
    
    def test_twelve_hour_pm_format(self):
        """Test parsing 12-hour PM format."""
        assert parse_time_to_military("6:00 PM") == 1800
        assert parse_time_to_military("11:30 PM") == 2330
        assert parse_time_to_military("12:00 PM") == 1200  # Noon
        assert parse_time_to_military("12:30 PM") == 1230
    
    def test_twelve_hour_single_digit_hour(self):
        """Test single-digit hours in 12-hour format."""
        assert parse_time_to_military("1:00 AM") == 100
        assert parse_time_to_military("9:45 AM") == 945
        assert parse_time_to_military("1:00 PM") == 1300
        assert parse_time_to_military("9:45 PM") == 2145
    
    def test_twenty_four_hour_format(self):
        """Test parsing 24-hour format."""
        assert parse_time_to_military("18:00") == 1800
        assert parse_time_to_military("23:59") == 2359
        assert parse_time_to_military("00:00") == 0
        assert parse_time_to_military("12:30") == 1230
        assert parse_time_to_military("06:15") == 615
    
    def test_numeric_string(self):
        """Test parsing plain numeric strings."""
        assert parse_time_to_military("1800") == 1800
        assert parse_time_to_military("0") == 0
        assert parse_time_to_military("2359") == 2359
        assert parse_time_to_military("600") == 600
    
    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        assert parse_time_to_military("  1800  ") == 1800
        assert parse_time_to_military(" 6:00 PM ") == 1800
        assert parse_time_to_military("  18:00  ") == 1800
    
    def test_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Could not parse time"):
            parse_time_to_military("invalid")
        
        with pytest.raises(ValueError, match="Could not parse time"):
            parse_time_to_military("25:00")  # Invalid hour
        
        with pytest.raises(ValueError, match="Could not parse time"):
            parse_time_to_military("12:60 PM")  # Invalid minute
        
        with pytest.raises(ValueError, match="Could not parse time"):
            parse_time_to_military("")  # Empty string
    
    def test_edge_cases(self):
        """Test edge cases and boundary values."""
        # Earliest time
        assert parse_time_to_military("12:00 AM") == 0
        assert parse_time_to_military("00:00") == 0
        
        # Latest time
        assert parse_time_to_military("11:59 PM") == 2359
        assert parse_time_to_military("23:59") == 2359
        
        # Noon and midnight
        assert parse_time_to_military("12:00 PM") == 1200
        assert parse_time_to_military("12:00 AM") == 0