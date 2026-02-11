"""
Interval Operations Module

Provides set-like operations on time intervals: union, intersection, subtraction.
Uses TimeInterval dataclass for type safety.

All operations treat adjacent intervals as mergeable and filter out zero-duration intervals.
"""

from typing import List
from datetime import time

from rehearsal_scheduler.models.intervals import TimeInterval


def interval_duration(interval: TimeInterval) -> int:
    """
    Calculate interval duration in minutes.
    
    Args:
        interval: TimeInterval to measure
        
    Returns:
        Duration in minutes
        
    Example:
        >>> interval_duration(TimeInterval(time(9, 0), time(12, 0)))
        180
    """
    return interval.duration_minutes()


def intervals_overlap(a: TimeInterval, b: TimeInterval) -> bool:
    """
    Check if two intervals overlap or are adjacent.
    
    Adjacent intervals (end of one == start of other) are considered overlapping
    for the purpose of merging.
    
    Args:
        a: First interval
        b: Second interval
        
    Returns:
        True if intervals overlap or are adjacent, False otherwise
        
    Example:
        >>> intervals_overlap(
        ...     TimeInterval(time(9, 0), time(12, 0)),
        ...     TimeInterval(time(11, 0), time(14, 0))
        ... )
        True
    """
    # Convert to minutes for easier comparison
    a_start = a.start.hour * 60 + a.start.minute
    a_end = a.end.hour * 60 + a.end.minute
    b_start = b.start.hour * 60 + b.start.minute
    b_end = b.end.hour * 60 + b.end.minute
    
    # Overlap if: max(starts) <= min(ends)
    # Using <= (not <) to treat adjacent as overlapping
    return max(a_start, b_start) <= min(a_end, b_end)


def intersect_intervals(a: TimeInterval, b: TimeInterval) -> List[TimeInterval]:
    """
    Find intersection of two intervals.
    
    Args:
        a: First interval
        b: Second interval
        
    Returns:
        List containing intersection interval, or empty list if no overlap
        
    Example:
        >>> intersect_intervals(
        ...     TimeInterval(time(9, 0), time(14, 0)),
        ...     TimeInterval(time(11, 0), time(16, 0))
        ... )
        [TimeInterval(start=time(11, 0), end=time(14, 0))]
    """
    # Convert to minutes
    a_start = a.start.hour * 60 + a.start.minute
    a_end = a.end.hour * 60 + a.end.minute
    b_start = b.start.hour * 60 + b.start.minute
    b_end = b.end.hour * 60 + b.end.minute
    
    # Calculate overlap
    overlap_start = max(a_start, b_start)
    overlap_end = min(a_end, b_end)
    
    # No overlap if start >= end
    if overlap_start >= overlap_end:
        return []
    
    # Convert back to time
    start_time = time(overlap_start // 60, overlap_start % 60)
    end_time = time(overlap_end // 60, overlap_end % 60)
    
    return [TimeInterval(start_time, end_time)]


def merge_adjacent_intervals(intervals: List[TimeInterval]) -> List[TimeInterval]:
    """
    Merge adjacent and overlapping intervals.
    
    Assumes intervals are already sorted by start time.
    
    Args:
        intervals: Sorted list of intervals
        
    Returns:
        List of merged intervals
    """
    if not intervals:
        return []
    
    merged = [intervals[0]]
    
    for current in intervals[1:]:
        last = merged[-1]
        
        # Check if current overlaps or is adjacent to last
        if intervals_overlap(last, current):
            # Merge by extending the end time
            last_end_mins = last.end.hour * 60 + last.end.minute
            curr_end_mins = current.end.hour * 60 + current.end.minute
            new_end_mins = max(last_end_mins, curr_end_mins)
            
            merged[-1] = TimeInterval(
                last.start,
                time(new_end_mins // 60, new_end_mins % 60)
            )
        else:
            # No overlap - add as separate interval
            merged.append(current)
    
    return merged


def union_intervals(intervals: List[TimeInterval]) -> List[TimeInterval]:
    """
    Merge intervals into consolidated ranges.
    
    Handles overlapping and adjacent intervals. Filters out zero-duration intervals.
    
    Args:
        intervals: List of intervals to merge
        
    Returns:
        Sorted list of non-overlapping, merged intervals
        
    Example:
        >>> union_intervals([
        ...     TimeInterval(time(9, 0), time(12, 0)),
        ...     TimeInterval(time(11, 0), time(14, 0)),
        ...     TimeInterval(time(16, 0), time(18, 0))
        ... ])
        [TimeInterval(time(9, 0), time(14, 0)), TimeInterval(time(16, 0), time(18, 0))]
    """
    if not intervals:
        return []
    
    # Filter out zero-duration intervals
    non_zero = [iv for iv in intervals if interval_duration(iv) > 0]

    if not non_zero:       # pragman: no cover
        return []
    
    # Sort by start time
    sorted_intervals = sorted(
        non_zero,
        key=lambda iv: (iv.start.hour * 60 + iv.start.minute)
    )
    
    # Merge adjacent/overlapping intervals
    return merge_adjacent_intervals(sorted_intervals)


def subtract_intervals(base: TimeInterval, subtracts: List[TimeInterval]) -> List[TimeInterval]:
    """
    Subtract multiple intervals from a base interval.
    
    Merges overlapping subtract intervals first, then removes them from base.
    
    Args:
        base: Base interval to subtract from
        subtracts: List of intervals to remove (use [interval] for single)
        
    Returns:
        List of remaining intervals
        
    Example:
        >>> # Single interval
        >>> subtract_intervals(
        ...     TimeInterval(time(9, 0), time(17, 0)),
        ...     [TimeInterval(time(12, 0), time(14, 0))]
        ... )
        [TimeInterval(time(9, 0), time(12, 0)), TimeInterval(time(14, 0), time(17, 0))]
        
        >>> # Multiple intervals
        >>> subtract_intervals(
        ...     TimeInterval(time(9, 0), time(18, 0)),
        ...     [TimeInterval(time(10, 0), time(11, 0)),
        ...      TimeInterval(time(14, 0), time(15, 0))]
        ... )
        [TimeInterval(time(9, 0), time(10, 0)),
         TimeInterval(time(11, 0), time(14, 0)),
         TimeInterval(time(15, 0), time(18, 0))]
    """
    if not subtracts:
        return [base]
    
    # Merge overlapping subtract intervals first
    merged_subtracts = union_intervals(subtracts)
    
    # Start with base interval
    remaining = [base]
    
    # Subtract each interval
    for sub in merged_subtracts:
        new_remaining = []
        for piece in remaining:
            # Inline the subtract logic (previously in subtract_interval)
            # Convert to minutes
            base_start = piece.start.hour * 60 + piece.start.minute
            base_end = piece.end.hour * 60 + piece.end.minute
            sub_start = sub.start.hour * 60 + sub.start.minute
            sub_end = sub.end.hour * 60 + sub.end.minute
            
            # No overlap - keep original piece
            if sub_end <= base_start or sub_start >= base_end:
                new_remaining.append(piece)
                continue
            
            # Complete overlap - skip piece (nothing left)
            if sub_start <= base_start and sub_end >= base_end:
                continue
            
            # Partial overlap - create remaining pieces
            # Left piece exists
            if base_start < sub_start:
                left_end = min(sub_start, base_end)
                new_remaining.append(TimeInterval(
                    time(base_start // 60, base_start % 60),
                    time(left_end // 60, left_end % 60)
                ))
            
            # Right piece exists
            if base_end > sub_end:
                right_start = max(sub_end, base_start)
                new_remaining.append(TimeInterval(
                    time(right_start // 60, right_start % 60),
                    time(base_end // 60, base_end % 60)
                ))
        
        remaining = new_remaining
        
        # Early exit if nothing left
        if not remaining:
            break
    
    return remaining