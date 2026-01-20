"""Tests for interval models."""

import pytest
from datetime import date, time
from rehearsal_scheduler.models.intervals import TimeInterval, DateInterval, VenueSlot


# TimeInterval tests

def test_create_valid_time_interval():
    """Test creating a valid time interval."""
    interval = TimeInterval(time(9, 0), time(17, 0))
    assert interval.start == time(9, 0)
    assert interval.end == time(17, 0)


def test_invalid_time_interval_raises_error():
    """Test that end before start raises error."""
    with pytest.raises(ValueError, match="must be before"):
        TimeInterval(time(17, 0), time(9, 0))


def test_time_interval_duration_minutes():
    """Test duration calculation."""
    interval = TimeInterval(time(9, 0), time(17, 30))
    assert interval.duration_minutes() == 510  # 8.5 hours


def test_time_interval_overlaps_true():
    """Test overlapping intervals."""
    i1 = TimeInterval(time(9, 0), time(12, 0))
    i2 = TimeInterval(time(11, 0), time(14, 0))
    assert i1.overlaps(i2)
    assert i2.overlaps(i1)


def test_time_interval_overlaps_false():
    """Test non-overlapping intervals."""
    i1 = TimeInterval(time(9, 0), time(12, 0))
    i2 = TimeInterval(time(13, 0), time(16, 0))
    assert not i1.overlaps(i2)
    assert not i2.overlaps(i1)


def test_time_interval_contains_time():
    """Test time containment."""
    interval = TimeInterval(time(9, 0), time(17, 0))
    assert interval.contains_time(time(12, 0))
    assert not interval.contains_time(time(8, 0))
    assert not interval.contains_time(time(18, 0))


def test_time_interval_from_strings_12hour():
    """Test parsing 12-hour format."""
    interval = TimeInterval.from_strings("9:00 AM", "5:00 PM")
    assert interval.start == time(9, 0)
    assert interval.end == time(17, 0)


def test_time_interval_from_strings_24hour():
    """Test parsing 24-hour format."""
    interval = TimeInterval.from_strings("09:00", "17:00")
    assert interval.start == time(9, 0)
    assert interval.end == time(17, 0)


# DateInterval tests

def test_create_single_date_interval():
    """Test single date interval."""
    interval = DateInterval(date(2025, 12, 25))
    assert interval.is_single_date()
    assert interval.contains_date(date(2025, 12, 25))
    assert not interval.contains_date(date(2025, 12, 26))


def test_create_date_range_interval():
    """Test date range interval."""
    interval = DateInterval(date(2025, 12, 20), date(2025, 12, 28))
    assert not interval.is_single_date()
    assert interval.contains_date(date(2025, 12, 25))
    assert not interval.contains_date(date(2025, 12, 29))


def test_invalid_date_interval_raises_error():
    """Test that end before start raises error."""
    with pytest.raises(ValueError, match="must be before"):
        DateInterval(date(2025, 12, 28), date(2025, 12, 20))


def test_date_interval_overlaps_true():
    """Test overlapping date ranges."""
    i1 = DateInterval(date(2025, 12, 20), date(2025, 12, 25))
    i2 = DateInterval(date(2025, 12, 23), date(2025, 12, 28))
    assert i1.overlaps(i2)
    assert i2.overlaps(i1)


def test_date_interval_overlaps_false():
    """Test non-overlapping date ranges."""
    i1 = DateInterval(date(2025, 12, 20), date(2025, 12, 22))
    i2 = DateInterval(date(2025, 12, 23), date(2025, 12, 25))
    assert not i1.overlaps(i2)
    assert not i2.overlaps(i1)


def test_date_interval_duration_days_single():
    """Test duration for single date."""
    interval = DateInterval(date(2025, 12, 25))
    assert interval.duration_days() == 1


def test_date_interval_duration_days_range():
    """Test duration for date range."""
    interval = DateInterval(date(2025, 12, 20), date(2025, 12, 28))
    assert interval.duration_days() == 9  # Inclusive


# VenueSlot tests

def test_create_venue_slot():
    """Test creating a venue slot."""
    time_int = TimeInterval(time(9, 0), time(17, 0))
    slot = VenueSlot("CC", "Tuesday", date(2025, 12, 23), time_int)
    
    assert slot.venue == "CC"
    assert slot.day_of_week == "tuesday"
    assert slot.available_minutes == 480
    assert slot.remaining_minutes == 480


def test_venue_slot_matches_day():
    """Test day matching."""
    time_int = TimeInterval(time(9, 0), time(17, 0))
    slot = VenueSlot("CC", "Tuesday", date(2025, 12, 23), time_int)
    
    assert slot.matches_day("Tuesday")
    assert slot.matches_day("TUESDAY")
    assert not slot.matches_day("Wednesday")


def test_venue_slot_can_fit():
    """Test time fit checking."""
    time_int = TimeInterval(time(9, 0), time(17, 0))
    slot = VenueSlot("CC", "Tuesday", date(2025, 12, 23), time_int)
    
    assert slot.can_fit(400)
    assert not slot.can_fit(500)


def test_venue_slot_allocate_success():
    """Test successful time allocation."""
    time_int = TimeInterval(time(9, 0), time(17, 0))
    slot = VenueSlot("CC", "Tuesday", date(2025, 12, 23), time_int)
    
    assert slot.allocate(100)
    assert slot.remaining_minutes == 380


def test_venue_slot_allocate_failure():
    """Test failed allocation (insufficient time)."""
    time_int = TimeInterval(time(9, 0), time(17, 0))
    slot = VenueSlot("CC", "Tuesday", date(2025, 12, 23), time_int)
    
    assert not slot.allocate(500)
    assert slot.remaining_minutes == 480  # Unchanged