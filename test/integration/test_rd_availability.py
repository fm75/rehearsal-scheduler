"""
Tests for RD availability and availability calculation functions.

Extends existing scheduling_catalog tests to cover new availability features.
"""

import pytest
import pandas as pd
from datetime import date, time

from rehearsal_scheduler.domain.scheduling_catalog import (
    find_rd_availability,
    find_availability_by_group,
    calculate_full_availability_for_group
)
from rehearsal_scheduler.constraints import RehearsalSlot
from rehearsal_scheduler.models.intervals import TimeInterval


# ============================================================================
# Test find_rd_availability
# ============================================================================

def test_find_rd_availability_no_constraints():
    """Test RDs with no constraints are not shown."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01', 'rd_02'],
        'full_name': ['Alice Director', 'Bob Director'],
        'constraints': ['', '']  # No constraints
    })
    
    result = find_rd_availability(slot, rd_constraints)
    
    # RDs with no constraints (full availability) should not be shown
    assert len(result) == 0


def test_find_rd_availability_partial():
    """Test RD with partial availability shows time windows."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01'],
        'full_name': ['Alice Director'],
        'constraints': ['Monday before 7:00 pm']  # Conflicts 6-7pm
    })
    
    result = find_rd_availability(slot, rd_constraints)
    
    assert len(result) == 1
    assert result[0].entity_id == 'rd_01'
    assert result[0].full_name == 'Alice Director'
    assert 'Available' in result[0].reason
    assert '7:00 pm' in result[0].reason
    assert '9:00 pm' in result[0].reason


def test_find_rd_availability_zero():
    """Test RD with zero availability shows unavailable."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01'],
        'full_name': ['Alice Director'],
        'constraints': ['Monday']  # Conflicts entire day
    })
    
    result = find_rd_availability(slot, rd_constraints)
    
    assert len(result) == 1
    assert result[0].entity_id == 'rd_01'
    assert '❌ Unavailable' in result[0].reason


def test_find_rd_availability_multiple_windows():
    """Test RD with multiple availability windows."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    # Conflicts 7-8pm, leaving 6-7pm and 8-9pm available
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01'],
        'full_name': ['Alice Director'],
        'constraints': ['Monday 7:00 pm - 8:00 pm']
    })
    
    result = find_rd_availability(slot, rd_constraints)
    
    assert len(result) == 1
    assert 'Available' in result[0].reason
    # Should show both windows separated by comma
    assert ',' in result[0].reason


def test_find_rd_availability_parse_error():
    """Test error handling for unparseable constraints."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01'],
        'full_name': ['Alice Director'],
        'constraints': ['INVALID CONSTRAINT FORMAT!!!']
    })
    
    result = find_rd_availability(slot, rd_constraints)
    
    assert len(result) == 1
    assert 'ERROR' in result[0].reason


# ============================================================================
# Test calculate_full_availability_for_group
# ============================================================================

def test_calculate_full_availability_for_group_all_available():
    """Test formatted output when all dancers available."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    slot_interval = TimeInterval(time(18, 0), time(21, 0))
    
    group_cast = pd.DataFrame({
        'd_01': ['1', '1'],
    }, index=['dancer_01', 'dancer_02'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01', 'dancer_02'],
        'full_name': ['Alice', 'Bob'],
        'constraints': ['', '']
    })
    
    result = calculate_full_availability_for_group(
        'd_01',
        slot_interval,
        group_cast,
        dancer_constraints,
        slot
    )
    
    # Should return formatted time range
    assert '6:00 pm' in result
    assert '9:00 pm' in result


def test_calculate_full_availability_for_group_no_overlap():
    """Test formatted output when no overlap."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    slot_interval = TimeInterval(time(18, 0), time(21, 0))
    
    group_cast = pd.DataFrame({
        'd_01': ['1', '1'],
    }, index=['dancer_01', 'dancer_02'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01', 'dancer_02'],
        'full_name': ['Alice', 'Bob'],
        'constraints': [
            'Monday',  # Alice completely unavailable
            ''
        ]
    })
    
    result = calculate_full_availability_for_group(
        'd_01',
        slot_interval,
        group_cast,
        dancer_constraints,
        slot
    )
    
    assert result == "None"


def test_calculate_full_availability_for_group_no_dancers():
    """Test handling group with no dancers."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    slot_interval = TimeInterval(time(18, 0), time(21, 0))
    
    group_cast = pd.DataFrame({
        'd_01': [],
    })
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': [],
        'full_name': [],
        'constraints': []
    })
    
    result = calculate_full_availability_for_group(
        'd_01',
        slot_interval,
        group_cast,
        dancer_constraints,
        slot
    )
    
    assert result == "No dancers"


# ============================================================================
# Test find_availability_by_group
# ============================================================================

def test_find_availability_by_group_partial_availability():
    """Test finding availability for groups with partial dancer availability."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    dance_groups = pd.DataFrame({
        'dg_id': ['d_01'],
        'dg_name': ['Test Dance'],
        'current_rd': ['rd_01'],
        'current_rd_name': ['Director']
    })
    
    group_cast = pd.DataFrame({
        'd_01': ['1', '1'],
    }, index=['dancer_01', 'dancer_02'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01', 'dancer_02'],
        'full_name': ['Alice', 'Bob'],
        'constraints': [
            'Monday before 7:00 pm',  # Partial
            ''  # Full
        ]
    })
    
    result = find_availability_by_group(
        slot,
        dance_groups,
        group_cast,
        dancer_constraints,
        set(),  # No ineligible groups
        calculate_full_availability=False
    )
    
    # Should show Alice (has constraints) but not Bob (full availability)
    assert 'd_01' in result
    assert len(result['d_01']) == 1
    assert result['d_01'][0].full_name == 'Alice'
    assert 'Available' in result['d_01'][0].reason


def test_find_availability_by_group_zero_availability():
    """Test dancer with zero availability is shown."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    dance_groups = pd.DataFrame({
        'dg_id': ['d_01'],
        'dg_name': ['Test Dance'],
        'current_rd': ['rd_01'],
        'current_rd_name': ['Director']
    })
    
    group_cast = pd.DataFrame({
        'd_01': ['1'],
    }, index=['dancer_01'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01'],
        'full_name': ['Alice'],
        'constraints': ['Monday']  # Entire day unavailable
    })
    
    result = find_availability_by_group(
        slot,
        dance_groups,
        group_cast,
        dancer_constraints,
        set(),
        calculate_full_availability=False
    )
    
    # Should show zero availability
    assert 'd_01' in result
    assert len(result['d_01']) == 1
    assert '❌ Unavailable' in result['d_01'][0].reason


def test_find_availability_by_group_with_full_calculation():
    """Test calculating 100% availability when flag is set."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    dance_groups = pd.DataFrame({
        'dg_id': ['d_01'],
        'dg_name': ['Test Dance'],
        'current_rd': ['rd_01'],
        'current_rd_name': ['Director']
    })
    
    group_cast = pd.DataFrame({
        'd_01': ['1', '1'],
    }, index=['dancer_01', 'dancer_02'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01', 'dancer_02'],
        'full_name': ['Alice', 'Bob'],
        'constraints': [
            'Monday before 7:00 pm',
            ''
        ]
    })
    
    result = find_availability_by_group(
        slot,
        dance_groups,
        group_cast,
        dancer_constraints,
        set(),
        calculate_full_availability=True
    )
    
    # Should return tuple: (list of constraints, full_availability_string)
    assert 'd_01' in result
    assert isinstance(result['d_01'], tuple)
    conflicts, full_avail = result['d_01']
    assert len(conflicts) == 1  # Only Alice (has constraints)
    assert '7:00 pm' in full_avail  # 100% window starts at 7pm


def test_find_availability_by_group_skip_ineligible():
    """Test that ineligible groups are skipped."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    dance_groups = pd.DataFrame({
        'dg_id': ['d_01', 'd_02'],
        'dg_name': ['Test Dance 1', 'Test Dance 2'],
        'current_rd': ['rd_01', 'rd_02'],
        'current_rd_name': ['Director 1', 'Director 2']
    })
    
    group_cast = pd.DataFrame({
        'd_01': ['1'],
        'd_02': ['1']
    }, index=['dancer_01'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01'],
        'full_name': ['Alice'],
        'constraints': ['Monday']
    })
    
    # d_01 is ineligible (RD unavailable)
    ineligible = {'d_01'}
    
    result = find_availability_by_group(
        slot,
        dance_groups,
        group_cast,
        dancer_constraints,
        ineligible,
        calculate_full_availability=False
    )
    
    # d_01 should be skipped, only d_02 processed
    assert 'd_01' not in result
    assert 'd_02' in result