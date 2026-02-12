"""
Tests for interval parsing utilities.
"""

import pytest
from datetime import time

from rehearsal_scheduler.models.intervals import TimeInterval
from rehearsal_scheduler.models.interval_parsing import (
    parse_time_string,
    parse_interval_string,
    parse_availability_string,
    does_duration_fit_in_intervals,
    find_best_fit_interval
)

# ============================================================================
# Test parse_time_string
# ============================================================================

def test_parse_time_morning():
    """Test parsing morning times."""
    assert parse_time_string("7:00 am") == time(7, 0)
    assert parse_time_string("11:30 am") == time(11, 30)


def test_parse_time_afternoon():
    """Test parsing afternoon/evening times."""
    assert parse_time_string("1:00 pm") == time(13, 0)
    assert parse_time_string("7:30 pm") == time(19, 30)
    assert parse_time_string("11:45 pm") == time(23, 45)


def test_parse_time_noon_midnight():
    """Test parsing noon and midnight edge cases."""
    assert parse_time_string("12:00 pm") == time(12, 0)  # Noon
    assert parse_time_string("12:00 am") == time(0, 0)   # Midnight
    assert parse_time_string("12:30 am") == time(0, 30)
    assert parse_time_string("12:30 pm") == time(12, 30)


def test_parse_time_whitespace():
    """Test parsing with extra whitespace."""
    assert parse_time_string("  7:00 pm  ") == time(19, 0)
    assert parse_time_string("7:00  pm") == time(19, 0)


def test_parse_time_case_insensitive():
    """Test parsing is case insensitive."""
    assert parse_time_string("7:00 PM") == time(19, 0)
    assert parse_time_string("7:00 Am") == time(7, 0)


def test_parse_time_invalid():
    """Test parsing invalid time strings raises error."""
    with pytest.raises(ValueError):
        parse_time_string("invalid")
    
    with pytest.raises(ValueError):
        parse_time_string("25:00 pm")
    
    with pytest.raises(ValueError):
        parse_time_string("7:00")  # Missing am/pm


# ============================================================================
# Test parse_interval_string
# ============================================================================

def test_parse_interval_basic():
    """Test parsing basic interval string."""
    interval = parse_interval_string("7:00 pm - 8:30 pm")
    
    assert interval.start == time(19, 0)
    assert interval.end == time(20, 30)


def test_parse_interval_morning():
    """Test parsing morning interval."""
    interval = parse_interval_string("9:00 am - 11:00 am")
    
    assert interval.start == time(9, 0)
    assert interval.end == time(11, 0)


def test_parse_interval_across_noon():
    """Test parsing interval across noon."""
    interval = parse_interval_string("11:00 am - 1:00 pm")
    
    assert interval.start == time(11, 0)
    assert interval.end == time(13, 0)


def test_parse_interval_whitespace():
    """Test parsing with extra whitespace."""
    interval = parse_interval_string("  7:00 pm  -  8:30 pm  ")
    
    assert interval.start == time(19, 0)
    assert interval.end == time(20, 30)


def test_parse_interval_invalid():
    """Test parsing invalid interval raises error."""
    with pytest.raises(ValueError):
        parse_interval_string("7:00 pm")  # Missing end time
    
    with pytest.raises(ValueError):
        parse_interval_string("7:00 pm to 8:00 pm")  # Wrong separator


# ============================================================================
# Test parse_availability_string
# ============================================================================

def test_parse_availability_single_interval():
    """Test parsing single interval."""
    intervals = parse_availability_string("7:00 pm - 8:30 pm")
    
    assert len(intervals) == 1
    assert intervals[0].start == time(19, 0)
    assert intervals[0].end == time(20, 30)


def test_parse_availability_multiple_intervals():
    """Test parsing comma-separated intervals."""
    intervals = parse_availability_string("7:00 pm - 8:00 pm, 9:00 pm - 9:30 pm")
    
    assert len(intervals) == 2
    assert intervals[0].start == time(19, 0)
    assert intervals[0].end == time(20, 0)
    assert intervals[1].start == time(21, 0)
    assert intervals[1].end == time(21, 30)


def test_parse_availability_empty():
    """Test parsing empty availability string."""
    assert parse_availability_string("") == []
    assert parse_availability_string("   ") == []


def test_parse_availability_with_whitespace():
    """Test parsing with extra whitespace around commas."""
    intervals = parse_availability_string("7:00 pm - 8:00 pm , 9:00 pm - 9:30 pm")
    
    assert len(intervals) == 2


def test_parse_availability_three_intervals():
    """Test parsing three intervals."""
    intervals = parse_availability_string(
        "9:00 am - 10:00 am, 11:00 am - 12:00 pm, 2:00 pm - 3:00 pm"
    )
    
    assert len(intervals) == 3
    assert intervals[0].start == time(9, 0)
    assert intervals[1].start == time(11, 0)
    assert intervals[2].start == time(14, 0)


# ============================================================================
# Test does_duration_fit_in_intervals
# ============================================================================

def test_duration_fits_in_single_interval():
    """Test duration that fits in a single interval."""
    intervals = [TimeInterval(time(19, 0), time(20, 30))]  # 90 minutes
    
    assert does_duration_fit_in_intervals(60, intervals) is True
    assert does_duration_fit_in_intervals(90, intervals) is True
    assert does_duration_fit_in_intervals(120, intervals) is False


def test_duration_fits_in_multiple_intervals():
    """Test duration that fits in one of multiple intervals."""
    intervals = [
        TimeInterval(time(19, 0), time(20, 0)),   # 60 minutes
        TimeInterval(time(21, 0), time(22, 30))   # 90 minutes
    ]
    
    assert does_duration_fit_in_intervals(45, intervals) is True
    assert does_duration_fit_in_intervals(75, intervals) is True
    assert does_duration_fit_in_intervals(100, intervals) is False


def test_duration_fits_empty_intervals():
    """Test with empty intervals list."""
    assert does_duration_fit_in_intervals(30, []) is False


def test_duration_fits_exact_match():
    """Test duration exactly matching interval length."""
    intervals = [TimeInterval(time(19, 0), time(20, 30))]  # 90 minutes
    
    assert does_duration_fit_in_intervals(90, intervals) is True


# ============================================================================
# Test find_best_fit_interval
# ============================================================================

def test_find_best_fit_single_interval():
    """Test finding best fit with single interval."""
    intervals = [TimeInterval(time(19, 0), time(21, 0))]  # 120 minutes
    
    best = find_best_fit_interval(60, intervals)
    
    assert best.start == time(19, 0)
    assert best.end == time(21, 0)


def test_find_best_fit_chooses_smallest():
    """Test that best fit chooses smallest sufficient interval."""
    intervals = [
        TimeInterval(time(19, 0), time(21, 0)),   # 120 minutes
        TimeInterval(time(14, 0), time(15, 30)),  # 90 minutes
        TimeInterval(time(9, 0), time(12, 0))     # 180 minutes
    ]
    
    best = find_best_fit_interval(60, intervals)
    
    # Should choose 90-minute interval (smallest that fits 60)
    assert best.start == time(14, 0)
    assert best.end == time(15, 30)


def test_find_best_fit_exact_match():
    """Test finding best fit when one interval matches exactly."""
    intervals = [
        TimeInterval(time(19, 0), time(21, 0)),   # 120 minutes
        TimeInterval(time(14, 0), time(15, 0))    # 60 minutes (exact)
    ]
    
    best = find_best_fit_interval(60, intervals)
    
    # Should choose exact match
    assert best.start == time(14, 0)
    assert best.end == time(15, 0)


def test_find_best_fit_no_fit():
    """Test error when no interval is large enough."""
    intervals = [
        TimeInterval(time(19, 0), time(19, 30)),  # 30 minutes
        TimeInterval(time(20, 0), time(20, 45))   # 45 minutes
    ]
    
    with pytest.raises(ValueError, match="No interval large enough"):
        find_best_fit_interval(60, intervals)


def test_find_best_fit_empty_list():
    """Test error with empty intervals list."""
    with pytest.raises(ValueError):
        find_best_fit_interval(60, [])