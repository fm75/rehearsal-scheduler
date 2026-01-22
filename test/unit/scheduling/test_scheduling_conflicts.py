"""
Comprehensive test coverage for scheduling/conflicts.py

Tests conflict detection logic used by domain modules.
"""

import pytest
from datetime import time, date
from rehearsal_scheduler.scheduling.conflicts import (
    check_slot_conflicts,
    check_slot_conflicts_from_dict
)
from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint,
    DateConstraint,
    DateRangeConstraint
)


# ============================================================================
# check_slot_conflicts Tests
# ============================================================================

def test_check_slot_conflicts_empty_constraints():
    """Test with empty constraints list."""
    result = check_slot_conflicts([], 'monday')
    
    assert result == []


def test_check_slot_conflicts_day_of_week_match():
    """Test DayOfWeekConstraint matching the slot day."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == ['monday']


def test_check_slot_conflicts_day_of_week_no_match():
    """Test DayOfWeekConstraint not matching the slot day."""
    constraints = [
        ('tuesday', DayOfWeekConstraint('tuesday'))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == []


def test_check_slot_conflicts_day_case_insensitive():
    """Test that day matching is case insensitive."""
    constraints = [
        ('Monday', DayOfWeekConstraint('monday'))
    ]
    
    result = check_slot_conflicts(constraints, 'MONDAY')
    
    assert result == ['Monday']


def test_check_slot_conflicts_time_on_day_match():
    """Test TimeOnDayConstraint with overlapping time."""
    constraints = [
        ('monday 14:00-16:00', TimeOnDayConstraint('monday', 1400, 1600))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_start=time(15, 0),
        slot_end=time(17, 0)
    )
    
    assert result == ['monday 14:00-16:00']


def test_check_slot_conflicts_time_on_day_no_overlap():
    """Test TimeOnDayConstraint with non-overlapping time."""
    constraints = [
        ('monday 9:00-11:00', TimeOnDayConstraint('monday', 900, 1100))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_start=time(14, 0),
        slot_end=time(16, 0)
    )
    
    assert result == []


def test_check_slot_conflicts_time_on_day_wrong_day():
    """Test TimeOnDayConstraint on different day."""
    constraints = [
        ('tuesday 14:00-16:00', TimeOnDayConstraint('tuesday', 1400, 1600))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_start=time(15, 0),
        slot_end=time(17, 0)
    )
    
    assert result == []


def test_check_slot_conflicts_time_without_slot_times():
    """Test TimeOnDayConstraint when slot times are not provided."""
    constraints = [
        ('monday 14:00-16:00', TimeOnDayConstraint('monday', 1400, 1600))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == []  # Can't check time overlap without slot times


def test_check_slot_conflicts_date_match():
    """Test DateConstraint matching the slot date."""
    constraints = [
        ('2025-01-20', DateConstraint(date(2025, 1, 20)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 20)
    )
    
    assert result == ['2025-01-20']


def test_check_slot_conflicts_date_no_match():
    """Test DateConstraint not matching the slot date."""
    constraints = [
        ('2025-01-21', DateConstraint(date(2025, 1, 21)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 20)
    )
    
    assert result == []


def test_check_slot_conflicts_date_without_slot_date():
    """Test DateConstraint when slot date is not provided."""
    constraints = [
        ('2025-01-20', DateConstraint(date(2025, 1, 20)))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == []


def test_check_slot_conflicts_date_range_match():
    """Test DateRangeConstraint with slot date in range."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 22)
    )
    
    assert result == ['Jan 20-25']


def test_check_slot_conflicts_date_range_start_boundary():
    """Test DateRangeConstraint at start boundary."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 20)
    )
    
    assert result == ['Jan 20-25']


def test_check_slot_conflicts_date_range_end_boundary():
    """Test DateRangeConstraint at end boundary."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 25)
    )
    
    assert result == ['Jan 20-25']


def test_check_slot_conflicts_date_range_before():
    """Test DateRangeConstraint with slot date before range."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 19)
    )
    
    assert result == []


def test_check_slot_conflicts_date_range_after():
    """Test DateRangeConstraint with slot date after range."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 26)
    )
    
    assert result == []


def test_check_slot_conflicts_date_range_without_slot_date():
    """Test DateRangeConstraint when slot date is not provided."""
    constraints = [
        ('Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == []


def test_check_slot_conflicts_tuple_of_constraints():
    """Test handling tuple of multiple constraints."""
    constraints = [
        ('monday, tuesday', (
            DayOfWeekConstraint('monday'),
            DayOfWeekConstraint('tuesday')
        ))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    assert result == ['monday, tuesday']


def test_check_slot_conflicts_multiple_constraints_one_conflict():
    """Test multiple constraints with only one conflicting."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday')),
        ('tuesday', DayOfWeekConstraint('tuesday')),
        ('wednesday', DayOfWeekConstraint('wednesday'))
    ]
    
    result = check_slot_conflicts(constraints, 'tuesday')
    
    assert result == ['tuesday']


def test_check_slot_conflicts_multiple_constraints_multiple_conflicts():
    """Test multiple constraints with multiple conflicts."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday')),
        ('2025-01-20', DateConstraint(date(2025, 1, 20)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 20)
    )
    
    assert result == ['monday', '2025-01-20']


def test_check_slot_conflicts_no_duplicate_tokens():
    """Test that same token is not added multiple times."""
    constraints = [
        ('monday, tuesday', (
            DayOfWeekConstraint('monday'),
            DayOfWeekConstraint('tuesday')
        ))
    ]
    
    result = check_slot_conflicts(constraints, 'monday')
    
    # Should only appear once even though tuple has multiple constraints
    assert result.count('monday, tuesday') == 1


def test_check_slot_conflicts_complex_time_overlap():
    """Test complex time interval overlaps."""
    # Constraint: 14:00-16:00, Slot: 15:30-17:00 (partial overlap)
    constraints = [
        ('afternoon', TimeOnDayConstraint('monday', 1400, 1600))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_start=time(15, 30),
        slot_end=time(17, 0)
    )
    
    assert result == ['afternoon']


def test_check_slot_conflicts_time_exact_match():
    """Test time constraint with exact time match."""
    constraints = [
        ('2pm-4pm', TimeOnDayConstraint('monday', 1400, 1600))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_start=time(14, 0),
        slot_end=time(16, 0)
    )
    
    assert result == ['2pm-4pm']


def test_check_slot_conflicts_all_constraint_types():
    """Test with all constraint types present."""
    constraints = [
        ('day', DayOfWeekConstraint('monday')),
        ('time', TimeOnDayConstraint('monday', 1400, 1600)),
        ('date', DateConstraint(date(2025, 1, 20))),
        ('range', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    result = check_slot_conflicts(
        constraints,
        'monday',
        slot_date=date(2025, 1, 20),
        slot_start=time(15, 0),
        slot_end=time(17, 0)
    )
    
    # All should conflict
    assert len(result) == 4
    assert 'day' in result
    assert 'time' in result
    assert 'date' in result
    assert 'range' in result


# ============================================================================
# check_slot_conflicts_from_dict Tests
# ============================================================================

def test_check_slot_conflicts_from_dict_basic():
    """Test basic functionality with dict slot."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }
    
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['monday']


def test_check_slot_conflicts_from_dict_with_time_overlap():
    """Test dict slot with time overlap."""
    constraints = [
        ('afternoon', TimeOnDayConstraint('monday', 1400, 1600))
    ]
    
    slot = {
        'day': 'monday',
        'date': '2025-01-20',
        'start': '15:00',
        'end': '17:00'
    }
    
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['afternoon']


def test_check_slot_conflicts_from_dict_with_date_match():
    """Test dict slot with date match."""
    constraints = [
        ('specific date', DateConstraint(date(2025, 1, 20)))
    ]
    
    slot = {
        'day': 'monday',
        'date': '01/20/2025',  # MM/DD/YYYY format
        'start': '14:00',
        'end': '16:00'
    }
    
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['specific date']


def test_check_slot_conflicts_from_dict_invalid_date():
    """Test dict slot with invalid date format."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'monday',
        'date': 'invalid-date',
        'start': '14:00',
        'end': '16:00'
    }
    
    # Should not crash, just skip date checks
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['monday']


def test_check_slot_conflicts_from_dict_missing_date():
    """Test dict slot with missing date key."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'monday',
        'start': '14:00',
        'end': '16:00'
    }
    
    # Should not crash, just skip date checks
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['monday']


def test_check_slot_conflicts_from_dict_invalid_time():
    """Test dict slot with invalid time format."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'monday',
        'date': '2025-01-20',
        'start': 'invalid',
        'end': '16:00'
    }
    
    # Should not crash, just skip time checks
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['monday']


def test_check_slot_conflicts_from_dict_missing_time():
    """Test dict slot with missing time keys."""
    constraints = [
        ('monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'monday',
        'date': '2025-01-20'
    }
    
    # Should not crash, just skip time checks
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['monday']


def test_check_slot_conflicts_from_dict_empty_constraints():
    """Test dict slot with empty constraints."""
    slot = {
        'day': 'monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }
    
    result = check_slot_conflicts_from_dict([], slot)
    
    assert result == []


def test_check_slot_conflicts_from_dict_case_handling():
    """Test that dict slot handles case properly."""
    constraints = [
        ('Monday', DayOfWeekConstraint('monday'))
    ]
    
    slot = {
        'day': 'MONDAY',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }
    
    result = check_slot_conflicts_from_dict(constraints, slot)
    
    assert result == ['Monday']


# ============================================================================
# Integration Tests
# ============================================================================

def test_realistic_conflict_scenario():
    """Test realistic scenario with multiple constraint types."""
    constraints = [
        ('unavailable mondays', DayOfWeekConstraint('monday')),
        ('busy 2-4pm tuesdays', TimeOnDayConstraint('tuesday', 1400, 1600)),
        ('vacation Jan 20-25', DateRangeConstraint(date(2025, 1, 20), date(2025, 1, 25)))
    ]
    
    # Monday slot - should conflict with DayOfWeekConstraint
    monday_slot = {
        'day': 'monday',
        'date': '01/13/2025',  # MM/DD/YYYY format
        'start': '10:00',
        'end': '12:00'
    }
    assert check_slot_conflicts_from_dict(constraints, monday_slot) == ['unavailable mondays']
    
    # Tuesday afternoon slot - should conflict with TimeOnDayConstraint
    tuesday_slot = {
        'day': 'tuesday',
        'date': '01/14/2025',  # MM/DD/YYYY format
        'start': '15:00',
        'end': '17:00'
    }
    assert check_slot_conflicts_from_dict(constraints, tuesday_slot) == ['busy 2-4pm tuesdays']
    
    # Vacation date slot - should conflict with DateRangeConstraint
    vacation_slot = {
        'day': 'wednesday',
        'date': '01/22/2025',  # MM/DD/YYYY format
        'start': '10:00',
        'end': '12:00'
    }
    assert check_slot_conflicts_from_dict(constraints, vacation_slot) == ['vacation Jan 20-25']
    
    # Non-conflicting slot
    clear_slot = {
        'day': 'thursday',
        'date': '01/30/2025',  # MM/DD/YYYY format
        'start': '10:00',
        'end': '12:00'
    }
    assert check_slot_conflicts_from_dict(constraints, clear_slot) == []