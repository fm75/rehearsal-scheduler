"""
Comprehensive test coverage for constraints.py

Tests all constraint dataclasses and their methods.
"""

import pytest
from datetime import date
from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint,
    DateConstraint,
    DateRangeConstraint,
    RehearsalSlot
)


# ============================================================================
# DayOfWeekConstraint Tests
# ============================================================================

def test_day_of_week_constraint_creation():
    """Test creating a DayOfWeekConstraint."""
    constraint = DayOfWeekConstraint(day_of_week='monday')
    
    assert constraint.day_of_week == 'monday'


def test_day_of_week_constraint_repr():
    """Test __repr__ method of DayOfWeekConstraint."""
    constraint = DayOfWeekConstraint(day_of_week='wednesday')
    
    result = repr(constraint)
    
    assert result == "DayOfWeekConstraint(day_of_week='wednesday')"
    assert 'wednesday' in result


def test_day_of_week_constraint_frozen():
    """Test that DayOfWeekConstraint is immutable (frozen)."""
    constraint = DayOfWeekConstraint(day_of_week='friday')
    
    with pytest.raises(AttributeError):
        constraint.day_of_week = 'monday'


def test_day_of_week_constraint_equality():
    """Test equality comparison of DayOfWeekConstraint."""
    constraint1 = DayOfWeekConstraint(day_of_week='monday')
    constraint2 = DayOfWeekConstraint(day_of_week='monday')
    constraint3 = DayOfWeekConstraint(day_of_week='tuesday')
    
    assert constraint1 == constraint2
    assert constraint1 != constraint3


# ============================================================================
# TimeOnDayConstraint Tests
# ============================================================================

def test_time_on_day_constraint_creation():
    """Test creating a TimeOnDayConstraint."""
    constraint = TimeOnDayConstraint(
        day_of_week='tuesday',
        start_time=900,
        end_time=1700
    )
    
    assert constraint.day_of_week == 'tuesday'
    assert constraint.start_time == 900
    assert constraint.end_time == 1700


def test_time_on_day_constraint_frozen():
    """Test that TimeOnDayConstraint is immutable (frozen)."""
    constraint = TimeOnDayConstraint('monday', 1000, 1200)
    
    with pytest.raises(AttributeError):
        constraint.start_time = 1100


def test_time_on_day_constraint_equality():
    """Test equality comparison of TimeOnDayConstraint."""
    constraint1 = TimeOnDayConstraint('monday', 900, 1200)
    constraint2 = TimeOnDayConstraint('monday', 900, 1200)
    constraint3 = TimeOnDayConstraint('monday', 1000, 1200)
    
    assert constraint1 == constraint2
    assert constraint1 != constraint3


# ============================================================================
# DateConstraint Tests
# ============================================================================

def test_date_constraint_creation():
    """Test creating a DateConstraint."""
    constraint = DateConstraint(date(2025, 1, 20))
    
    assert constraint.date == date(2025, 1, 20)


def test_date_constraint_repr():
    """Test __repr__ method of DateConstraint."""
    constraint = DateConstraint(date(2025, 3, 15))
    
    result = repr(constraint)
    
    assert result == "DateConstraint(date=2025-03-15)"
    assert '2025-03-15' in result


def test_date_constraint_equality_same_date():
    """Test DateConstraint equality with same date."""
    constraint1 = DateConstraint(date(2025, 1, 20))
    constraint2 = DateConstraint(date(2025, 1, 20))
    
    assert constraint1 == constraint2


def test_date_constraint_equality_different_date():
    """Test DateConstraint inequality with different date."""
    constraint1 = DateConstraint(date(2025, 1, 20))
    constraint2 = DateConstraint(date(2025, 1, 21))
    
    assert constraint1 != constraint2


def test_date_constraint_equality_different_type():
    """Test DateConstraint equality with different type."""
    constraint = DateConstraint(date(2025, 1, 20))
    
    assert constraint != "not a constraint"
    assert constraint != 123
    assert constraint != None


# ============================================================================
# DateRangeConstraint Tests
# ============================================================================

def test_date_range_constraint_creation():
    """Test creating a DateRangeConstraint."""
    constraint = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    
    assert constraint.start_date == date(2025, 1, 20)
    assert constraint.end_date == date(2025, 1, 25)


def test_date_range_constraint_same_start_and_end():
    """Test DateRangeConstraint with same start and end date."""
    constraint = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 20)
    )
    
    assert constraint.start_date == constraint.end_date


def test_date_range_constraint_invalid_range_raises_error():
    """Test that DateRangeConstraint raises ValueError when end < start."""
    with pytest.raises(ValueError, match="end_date must be >= start_date"):
        DateRangeConstraint(
            start_date=date(2025, 1, 25),
            end_date=date(2025, 1, 20)
        )


def test_date_range_constraint_repr():
    """Test __repr__ method of DateRangeConstraint."""
    constraint = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    
    result = repr(constraint)
    
    assert result == "DateRangeConstraint(start=2025-01-20, end=2025-01-25)"
    assert '2025-01-20' in result
    assert '2025-01-25' in result


def test_date_range_constraint_equality_same_range():
    """Test DateRangeConstraint equality with same range."""
    constraint1 = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    constraint2 = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    
    assert constraint1 == constraint2


def test_date_range_constraint_equality_different_start():
    """Test DateRangeConstraint inequality with different start date."""
    constraint1 = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    constraint2 = DateRangeConstraint(
        start_date=date(2025, 1, 21),
        end_date=date(2025, 1, 25)
    )
    
    assert constraint1 != constraint2


def test_date_range_constraint_equality_different_end():
    """Test DateRangeConstraint inequality with different end date."""
    constraint1 = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    constraint2 = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 26)
    )
    
    assert constraint1 != constraint2


def test_date_range_constraint_equality_different_type():
    """Test DateRangeConstraint equality with different type."""
    constraint = DateRangeConstraint(
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )
    
    assert constraint != "not a constraint"
    assert constraint != 123
    assert constraint != None
    assert constraint != DateConstraint(date(2025, 1, 20))


# ============================================================================
# RehearsalSlot Tests
# ============================================================================

def test_rehearsal_slot_creation():
    """Test creating a RehearsalSlot."""
    slot = RehearsalSlot(
        rehearsal_date=date(2025, 1, 20),
        day_of_week='monday',
        start_time=1400,
        end_time=1600
    )
    
    assert slot.rehearsal_date == date(2025, 1, 20)
    assert slot.day_of_week == 'monday'
    assert slot.start_time == 1400
    assert slot.end_time == 1600


def test_rehearsal_slot_frozen():
    """Test that RehearsalSlot is immutable (frozen)."""
    slot = RehearsalSlot(
        rehearsal_date=date(2025, 1, 20),
        day_of_week='monday',
        start_time=1400,
        end_time=1600
    )
    
    with pytest.raises(AttributeError):
        slot.start_time = 1500


def test_rehearsal_slot_equality():
    """Test equality comparison of RehearsalSlot."""
    slot1 = RehearsalSlot(date(2025, 1, 20), 'monday', 1400, 1600)
    slot2 = RehearsalSlot(date(2025, 1, 20), 'monday', 1400, 1600)
    slot3 = RehearsalSlot(date(2025, 1, 21), 'tuesday', 1400, 1600)
    
    assert slot1 == slot2
    assert slot1 != slot3


def test_rehearsal_slot_with_different_times():
    """Test RehearsalSlot with various time combinations."""
    morning_slot = RehearsalSlot(date(2025, 1, 20), 'monday', 900, 1100)
    afternoon_slot = RehearsalSlot(date(2025, 1, 20), 'monday', 1400, 1700)
    evening_slot = RehearsalSlot(date(2025, 1, 20), 'monday', 1800, 2100)
    
    assert morning_slot != afternoon_slot
    assert afternoon_slot != evening_slot
    assert morning_slot.start_time < afternoon_slot.start_time < evening_slot.start_time


# ============================================================================
# Integration Tests
# ============================================================================

def test_multiple_constraint_types_together():
    """Test using multiple constraint types together."""
    constraints = [
        DayOfWeekConstraint('monday'),
        TimeOnDayConstraint('tuesday', 900, 1200),
        DateConstraint(date(2025, 1, 20)),
        DateRangeConstraint(date(2025, 2, 1), date(2025, 2, 10))
    ]
    
    assert len(constraints) == 4
    assert isinstance(constraints[0], DayOfWeekConstraint)
    assert isinstance(constraints[1], TimeOnDayConstraint)
    assert isinstance(constraints[2], DateConstraint)
    assert isinstance(constraints[3], DateRangeConstraint)


def test_constraint_in_collection():
    """Test that constraints work properly in sets and dicts."""
    constraint1 = DayOfWeekConstraint('monday')
    constraint2 = DayOfWeekConstraint('monday')
    constraint3 = DayOfWeekConstraint('tuesday')
    
    # Should be hashable and work in sets
    constraint_set = {constraint1, constraint2, constraint3}
    assert len(constraint_set) == 2  # constraint1 and constraint2 are equal
    
    # Should work as dict keys
    constraint_dict = {
        constraint1: 'first',
        constraint3: 'second'
    }
    assert len(constraint_dict) == 2


def test_date_range_constraint_edge_case_very_long_range():
    """Test DateRangeConstraint with a very long date range."""
    constraint = DateRangeConstraint(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31)
    )
    
    assert constraint.start_date == date(2025, 1, 1)
    assert constraint.end_date == date(2025, 12, 31)


def test_time_on_day_constraint_edge_times():
    """Test TimeOnDayConstraint with edge case times."""
    # Early morning
    early = TimeOnDayConstraint('monday', 0, 100)
    assert early.start_time == 0
    
    # Late night
    late = TimeOnDayConstraint('friday', 2300, 2359)
    assert late.end_time == 2359
    
    # Full day
    full_day = TimeOnDayConstraint('saturday', 0, 2359)
    assert full_day.start_time == 0
    assert full_day.end_time == 2359