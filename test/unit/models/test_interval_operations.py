"""
Unit tests for interval operations module.

Tests interval arithmetic operations: union, intersection, subtraction, etc.
Uses TimeInterval dataclass from models.
"""

import pytest
from datetime import time

from rehearsal_scheduler.models.intervals import TimeInterval
from rehearsal_scheduler.models.interval_operations import (
    union_intervals,
    intersect_intervals,
    subtract_intervals,
    intervals_overlap,
    interval_duration,
    merge_adjacent_intervals
)


# ============================================================================
# Test interval_duration
# ============================================================================

def test_simple_duration():
    """Test basic duration calculation."""
    interval = TimeInterval(time(9, 0), time(12, 0))  # 9 AM - 12 PM
    assert interval_duration(interval) == 180


def test_duration_across_noon():
    """Test duration across noon boundary."""
    interval = TimeInterval(time(11, 30), time(13, 30))  # 11:30 AM - 1:30 PM
    assert interval_duration(interval) == 120


def test_duration_with_minutes():
    """Test duration with non-zero minutes."""
    interval = TimeInterval(time(9, 15), time(10, 45))
    assert interval_duration(interval) == 90


# Note: Zero-duration intervals (start == end) are not valid TimeInterval objects
# The dataclass enforces start < end, so they're automatically filtered


# ============================================================================
# Test intervals_overlap
# ============================================================================

def test_overlapping_intervals():
    """Test intervals that overlap."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(11, 0), time(14, 0))
    assert intervals_overlap(a, b) is True


def test_non_overlapping_intervals():
    """Test intervals that don't overlap."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(13, 0), time(14, 0))
    assert intervals_overlap(a, b) is False


def test_adjacent_intervals_overlap():
    """Test adjacent intervals (touch but don't overlap)."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(12, 0), time(14, 0))
    # Adjacent intervals should be treated as overlapping for merging
    assert intervals_overlap(a, b) is True


def test_contained_interval_overlaps():
    """Test interval completely contained in another."""
    a = TimeInterval(time(9, 0), time(17, 0))
    b = TimeInterval(time(11, 0), time(14, 0))
    assert intervals_overlap(a, b) is True


def test_identical_intervals_overlap():
    """Test identical intervals."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(9, 0), time(12, 0))
    assert intervals_overlap(a, b) is True


# ============================================================================
# Test intersect_intervals
# ============================================================================

def test_intersect_partial_overlap():
    """Test partial overlap returns intersection."""
    a = TimeInterval(time(9, 0), time(14, 0))
    b = TimeInterval(time(11, 0), time(16, 0))
    
    result = intersect_intervals(a, b)
    
    assert len(result) == 1
    assert result[0].start == time(11, 0)
    assert result[0].end == time(14, 0)


def test_intersect_no_overlap():
    """Test no overlap returns empty list."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(14, 0), time(16, 0))
    
    result = intersect_intervals(a, b)
    
    assert len(result) == 0


def test_intersect_contained_interval():
    """Test one interval contained in another."""
    a = TimeInterval(time(9, 0), time(17, 0))
    b = TimeInterval(time(11, 0), time(14, 0))
    
    result = intersect_intervals(a, b)
    
    assert len(result) == 1
    assert result[0].start == time(11, 0)
    assert result[0].end == time(14, 0)


def test_intersect_adjacent_intervals():
    """Test adjacent intervals have no intersection area."""
    a = TimeInterval(time(9, 0), time(12, 0))
    b = TimeInterval(time(12, 0), time(14, 0))
    
    result = intersect_intervals(a, b)
    
    # Adjacent intervals touch but have no overlapping area
    # intervals_overlap() returns True for merging purposes, but
    # intersect_intervals() returns empty since there's no actual overlap
    assert len(result) == 0


# ============================================================================
# Test subtract_intervals (handles both single and multiple)
# ============================================================================

def test_subtract_single_from_middle():
    """Test subtracting single interval from middle creates two pieces."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(12, 0), time(14, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 2
    assert result[0].start == time(9, 0)
    assert result[0].end == time(12, 0)
    assert result[1].start == time(14, 0)
    assert result[1].end == time(17, 0)


def test_subtract_single_from_beginning():
    """Test subtracting from beginning."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(8, 0), time(10, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 1
    assert result[0].start == time(10, 0)
    assert result[0].end == time(17, 0)


def test_subtract_single_from_end():
    """Test subtracting from end."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(16, 0), time(19, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(16, 0)


def test_subtract_single_no_overlap():
    """Test subtracting non-overlapping returns original."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(18, 0), time(19, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(17, 0)


def test_subtract_single_completely():
    """Test subtracting entire interval returns empty."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(8, 0), time(18, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 0


def test_subtract_single_exact_match():
    """Test subtracting exact same interval returns empty."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtract = [TimeInterval(time(9, 0), time(17, 0))]
    
    result = subtract_intervals(base, subtract)
    
    assert len(result) == 0


def test_subtract_two_non_overlapping():
    """Test subtracting two non-overlapping intervals."""
    base = TimeInterval(time(9, 0), time(18, 0))
    subtracts = [
        TimeInterval(time(10, 0), time(11, 0)),
        TimeInterval(time(14, 0), time(15, 0))
    ]
    
    result = subtract_intervals(base, subtracts)
    
    assert len(result) == 3
    assert result[0].start == time(9, 0)
    assert result[0].end == time(10, 0)
    assert result[1].start == time(11, 0)
    assert result[1].end == time(14, 0)
    assert result[2].start == time(15, 0)
    assert result[2].end == time(18, 0)


def test_subtract_overlapping_intervals():
    """Test subtracting overlapping intervals."""
    base = TimeInterval(time(9, 0), time(18, 0))
    subtracts = [
        TimeInterval(time(10, 0), time(12, 0)),
        TimeInterval(time(11, 0), time(14, 0))  # Overlaps with previous
    ]
    
    result = subtract_intervals(base, subtracts)
    
    # Should merge the overlapping subtracts first
    assert len(result) == 2
    assert result[0].start == time(9, 0)
    assert result[0].end == time(10, 0)
    assert result[1].start == time(14, 0)
    assert result[1].end == time(18, 0)


def test_subtract_empty_list():
    """Test subtracting empty list returns original."""
    base = TimeInterval(time(9, 0), time(17, 0))
    
    result = subtract_intervals(base, [])
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(17, 0)


# ============================================================================
# Test union_intervals
# ============================================================================

def test_union_overlapping():
    """Test merging overlapping intervals."""
    intervals = [
        TimeInterval(time(9, 0), time(12, 0)),
        TimeInterval(time(11, 0), time(14, 0)),
        TimeInterval(time(16, 0), time(18, 0))
    ]
    
    result = union_intervals(intervals)
    
    assert len(result) == 2
    assert result[0].start == time(9, 0)
    assert result[0].end == time(14, 0)
    assert result[1].start == time(16, 0)
    assert result[1].end == time(18, 0)


def test_union_adjacent():
    """Test merging adjacent intervals."""
    intervals = [
        TimeInterval(time(9, 0), time(12, 0)),
        TimeInterval(time(12, 0), time(14, 0))
    ]
    
    result = union_intervals(intervals)
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(14, 0)


def test_union_contained():
    """Test interval contained in another."""
    intervals = [
        TimeInterval(time(9, 0), time(17, 0)),
        TimeInterval(time(11, 0), time(14, 0))
    ]
    
    result = union_intervals(intervals)
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(17, 0)


def test_union_no_overlap():
    """Test non-overlapping intervals stay separate."""
    intervals = [
        TimeInterval(time(9, 0), time(11, 0)),
        TimeInterval(time(13, 0), time(15, 0)),
        TimeInterval(time(17, 0), time(19, 0))
    ]
    
    result = union_intervals(intervals)
    
    assert len(result) == 3


def test_union_unsorted_input():
    """Test that unsorted intervals are handled correctly."""
    intervals = [
        TimeInterval(time(16, 0), time(18, 0)),
        TimeInterval(time(9, 0), time(12, 0)),
        TimeInterval(time(11, 0), time(14, 0))
    ]
    
    result = union_intervals(intervals)
    
    assert len(result) == 2
    assert result[0].start == time(9, 0)
    assert result[0].end == time(14, 0)
    assert result[1].start == time(16, 0)
    assert result[1].end == time(18, 0)


def test_union_empty_list():
    """Test empty list returns empty."""
    result = union_intervals([])
    assert len(result) == 0


def test_subtract_multiple_with_complete_removal():
    """Test early exit when all pieces are removed."""
    base = TimeInterval(time(9, 0), time(17, 0))
    subtracts = [
        TimeInterval(time(8, 0), time(18, 0)),  # Removes everything
        TimeInterval(time(19, 0), time(20, 0))  # Would process but shouldn't (early exit)
    ]
    
    result = subtract_intervals(base, subtracts)
    
    assert len(result) == 0  # Everything removed, early exit triggered


def test_subtract_early_exit_when_nothing_remains():
    """Test early exit when first subtract removes everything."""
    base = TimeInterval(time(12, 0), time(14, 0))
    subtracts = [
        TimeInterval(time(10, 0), time(16, 0)),  # Completely covers base
        TimeInterval(time(18, 0), time(20, 0))   # Non-overlapping, shouldn't process
    ]
    
    result = subtract_intervals(base, subtracts)
    
    assert len(result) == 0
# Note: Zero-duration intervals not tested since TimeInterval enforces start < end


def test_subtract_early_exit_on_second_interval():
    """Test early exit when second subtract removes all remaining pieces."""
    base = TimeInterval(time(9, 0), time(18, 0))
    subtracts = [
        TimeInterval(time(10, 0), time(12, 0)),  # Leaves (9-10, 12-18)
        TimeInterval(time(8, 0), time(20, 0)),   # Removes everything that remains
        TimeInterval(time(19, 0), time(21, 0))   # Would process but break stops it
    ]
    
    result = subtract_intervals(base, subtracts)
    
    assert len(result) == 0

# ============================================================================
# Test merge_adjacent_intervals
# ============================================================================

def test_merge_two_adjacent():
    """Test merging two adjacent intervals."""
    intervals = [
        TimeInterval(time(9, 0), time(12, 0)),
        TimeInterval(time(12, 0), time(14, 0))
    ]
    
    result = merge_adjacent_intervals(intervals)
    
    assert len(result) == 1
    assert result[0].start == time(9, 0)
    assert result[0].end == time(14, 0)


def test_merge_no_merge_needed():
    """Test intervals with gaps are not merged."""
    intervals = [
        TimeInterval(time(9, 0), time(11, 0)),
        TimeInterval(time(13, 0), time(15, 0))
    ]
    
    result = merge_adjacent_intervals(intervals)
    
    assert len(result) == 2

def test_merge_empty():
    """Test intervals with gaps are not merged."""
    intervals = []
    
    result = merge_adjacent_intervals(intervals)
    
    assert len(result) == 0