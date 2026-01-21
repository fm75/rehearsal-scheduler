"""
Tests for conflict analyzer domain logic.
"""

import pytest
from rehearsal_scheduler.domain.conflict_analyzer import (
    ConflictAnalyzer,
    ConflictReport
)
from datetime import date, time


# Tests for ConflictReport dataclass

def test_conflict_report_has_conflicts():
    """Test has_conflicts property when conflicts exist."""
    report = ConflictReport(
        conflicts=[{'rhd_id': 'rd1', 'venue': 'Studio A'}],
        rds_with_conflicts=['rd1'],
        total_conflicts=1,
        rd_dances={'rd1': ['dance1']}
    )
    
    assert report.has_conflicts
    assert report.total_conflicts == 1


def test_conflict_report_no_conflicts():
    """Test has_conflicts property when no conflicts."""
    report = ConflictReport(
        conflicts=[],
        rds_with_conflicts=[],
        total_conflicts=0,
        rd_dances={}
    )
    
    assert not report.has_conflicts
    assert report.total_conflicts == 0


# Tests for ConflictAnalyzer

def test_conflict_analyzer_no_conflicts():
    """Test analyzer when there are no conflicts."""
    def mock_validate(token):
        return ('parsed', None)
    
    def mock_check_slot(constraints, day, slot_date, start_time, end_time):
        return []  # No conflicts
    
    def mock_parse_date(date_str):
        return date(2026, 1, 20)
    
    def mock_parse_time(time_str):
        return time(18, 0)
    
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = ConflictAnalyzer(
        mock_validate,
        mock_check_slot,
        mock_parse_date,
        mock_parse_time,
        mock_time_to_minutes
    )
    
    rhd_conflicts = [
        {'rhd_id': 'rd1', 'conflicts': 'Monday'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Tuesday', 'date': '1/21/26',
         'start': '6:00 PM', 'end': '8:00 PM'}
    ]
    
    dance_map = [
        {'dance_id': 'dance1', 'rhd_id': 'rd1'}
    ]
    
    report = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    assert not report.has_conflicts
    assert len(report.conflicts) == 0
    assert len(report.rds_with_conflicts) == 0


def test_conflict_analyzer_finds_conflicts():
    """Test analyzer finds conflicts when RD is unavailable."""
    def mock_validate(token):
        return ('parsed', None)
    
    def mock_check_slot(constraints, day, slot_date, start_time, end_time):
        # RD has conflict on Monday
        if day == 'Monday':
            return ['Monday']
        return []
    
    def mock_parse_date(date_str):
        return date(2026, 1, 20)
    
    def mock_parse_time(time_str):
        return time(18, 0)
    
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = ConflictAnalyzer(
        mock_validate,
        mock_check_slot,
        mock_parse_date,
        mock_parse_time,
        mock_time_to_minutes
    )
    
    rhd_conflicts = [
        {'rhd_id': 'rd1', 'conflicts': 'Monday'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '8:00 PM'}
    ]
    
    dance_map = [
        {'dance_id': 'dance1', 'rhd_id': 'rd1'}
    ]
    
    report = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    assert report.has_conflicts
    assert len(report.conflicts) == 1
    assert report.conflicts[0]['rhd_id'] == 'rd1'
    assert report.conflicts[0]['venue'] == 'Studio A'
    assert 'Monday' in report.conflicts[0]['conflicting_constraints']
    assert 'rd1' in report.rds_with_conflicts


def test_conflict_analyzer_tracks_affected_dances():
    """Test that affected dances are tracked in conflicts."""
    def mock_validate(token):
        return ('parsed', None)
    
    def mock_check_slot(constraints, day, slot_date, start_time, end_time):
        return ['Monday']  # Conflict
    
    def mock_parse_date(date_str):
        return date(2026, 1, 20)
    
    def mock_parse_time(time_str):
        return time(18, 0)
    
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = ConflictAnalyzer(
        mock_validate,
        mock_check_slot,
        mock_parse_date,
        mock_parse_time,
        mock_time_to_minutes
    )
    
    rhd_conflicts = [
        {'rhd_id': 'rd1', 'conflicts': 'Monday'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '8:00 PM'}
    ]
    
    dance_map = [
        {'dance_id': 'dance1', 'rhd_id': 'rd1'},
        {'dance_id': 'dance2', 'rhd_id': 'rd1'}
    ]
    
    report = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    # Should be sorted alphabetically
    assert report.rds_with_conflicts == ['rd1', ]