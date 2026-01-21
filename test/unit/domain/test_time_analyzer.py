"""
Tests for time analyzer domain logic.
"""

import pytest
from rehearsal_scheduler.domain.time_analyzer import (
    TimeAnalyzer,
    TimeAnalysisResult
)
from datetime import time


# Tests for TimeAnalysisResult dataclass

def test_time_analysis_result_has_deficit():
    """Test has_deficit property when requested > available."""
    result = TimeAnalysisResult(
        total_requested=100,
        total_available=80,
        deficit=20,
        requests_by_director={},
        venue_slots=[],
        missing_requests=[]
    )
    
    assert result.has_deficit
    assert not result.has_surplus
    assert not result.is_perfect_match


def test_time_analysis_result_has_surplus():
    """Test has_surplus property when available > requested."""
    result = TimeAnalysisResult(
        total_requested=80,
        total_available=100,
        deficit=-20,
        requests_by_director={},
        venue_slots=[],
        missing_requests=[]
    )
    
    assert result.has_surplus
    assert not result.has_deficit
    assert not result.is_perfect_match
    assert result.surplus == 20


def test_time_analysis_result_perfect_match():
    """Test is_perfect_match property when requested == available."""
    result = TimeAnalysisResult(
        total_requested=100,
        total_available=100,
        deficit=0,
        requests_by_director={},
        venue_slots=[],
        missing_requests=[]
    )
    
    assert result.is_perfect_match
    assert not result.has_deficit
    assert not result.has_surplus


def test_time_analysis_result_utilization_pct():
    """Test utilization percentage calculation."""
    result = TimeAnalysisResult(
        total_requested=75,
        total_available=100,
        deficit=-25,
        requests_by_director={},
        venue_slots=[],
        missing_requests=[]
    )
    
    assert result.utilization_pct == 75.0


def test_time_analysis_result_utilization_pct_zero_available():
    """Test utilization percentage when available is zero."""
    result = TimeAnalysisResult(
        total_requested=0,
        total_available=0,
        deficit=0,
        requests_by_director={},
        venue_slots=[],
        missing_requests=[]
    )
    
    assert result.utilization_pct == 0.0


# Tests for TimeAnalyzer

def test_time_analyzer_basic_analysis():
    """Test basic time analysis with simple data."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '60'},
        {'number_id': 'dance2', 'rhd_id': 'rd1', 'min_requested': '30'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '8:00 PM'}
    ]
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    assert result.total_requested == 90
    assert result.total_available == 120
    assert result.deficit == -30
    assert result.has_surplus
    assert 'rd1' in result.requests_by_director


def test_time_analyzer_with_allocated_column():
    """Test analyzer using min_allocated instead of min_requested."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 
         'min_requested': '60', 'min_allocated': '45'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '7:00 PM'}
    ]
    
    result = analyzer.analyze(time_requests, venue_schedule, use_allocated=True)
    
    assert result.total_requested == 45  # Uses allocated, not requested


def test_time_analyzer_groups_by_director():
    """Test that requests are grouped by director."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '60'},
        {'number_id': 'dance2', 'rhd_id': 'rd1', 'min_requested': '30'},
        {'number_id': 'dance3', 'rhd_id': 'rd2', 'min_requested': '45'}
    ]
    
    venue_schedule = []
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    assert len(result.requests_by_director) == 2
    assert result.requests_by_director['rd1']['total'] == 90
    assert result.requests_by_director['rd2']['total'] == 45
    assert len(result.requests_by_director['rd1']['dances']) == 2
    assert len(result.requests_by_director['rd2']['dances']) == 1


def test_time_analyzer_tracks_missing_requests():
    """Test that missing time requests are tracked."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '60'},
        {'number_id': 'dance2', 'rhd_id': 'rd1', 'min_requested': ''},  # Empty
        {'number_id': 'dance3', 'rhd_id': 'rd2'}  # Missing column
    ]
    
    venue_schedule = []
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    assert len(result.missing_requests) == 2
    assert 'dance2' in result.missing_requests
    assert 'dance3' in result.missing_requests


def test_time_analyzer_handles_invalid_minutes():
    """Test that invalid minute values are skipped."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '60'},
        {'number_id': 'dance2', 'rhd_id': 'rd1', 'min_requested': 'invalid'}
    ]
    
    venue_schedule = []
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    # Should only count the valid one
    assert result.total_requested == 60


def test_time_analyzer_calculates_venue_durations():
    """Test that venue slot durations are calculated correctly."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = []
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '8:00 PM'},
        {'venue': 'Studio B', 'day': 'Tuesday', 'date': '1/21/26',
         'start': '5:00 PM', 'end': '6:30 PM'}
    ]
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    assert len(result.venue_slots) == 2
    assert result.venue_slots[0]['duration'] == 120  # 2 hours
    assert result.venue_slots[1]['duration'] == 90   # 1.5 hours
    assert result.total_available == 210


def test_time_analyzer_skips_invalid_times():
    """Test that venue slots with invalid times are skipped."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = []
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': 'invalid', 'end': '8:00 PM'},
        {'venue': 'Studio B', 'day': 'Tuesday', 'date': '1/21/26',
         'start': '5:00 PM', 'end': '6:00 PM'}
    ]
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    # Should only count the valid slot
    assert len(result.venue_slots) == 1
    assert result.total_available == 60


def test_time_analyzer_empty_data():
    """Test analyzer with empty data."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    result = analyzer.analyze([], [])
    
    assert result.total_requested == 0
    assert result.total_available == 0
    assert result.deficit == 0
    assert result.is_perfect_match
    assert len(result.requests_by_director) == 0
    assert len(result.venue_slots) == 0


def test_time_analyzer_calculates_deficit():
    """Test deficit calculation when insufficient time."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '120'}
    ]
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '7:00 PM'}  # Only 60 minutes
    ]
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    assert result.deficit == 60  # Need 60 more minutes
    assert result.has_deficit


def test_time_analyzer_dance_details_in_director_group():
    """Test that dance details are preserved in director grouping."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    time_requests = [
        {'number_id': 'dance1', 'rhd_id': 'rd1', 'min_requested': '60'},
        {'number_id': 'dance2', 'rhd_id': 'rd1', 'min_requested': '30'}
    ]
    
    venue_schedule = []
    
    result = analyzer.analyze(time_requests, venue_schedule)
    
    dances = result.requests_by_director['rd1']['dances']
    assert dances[0]['number_id'] == 'dance1'
    assert dances[0]['minutes'] == 60
    assert dances[1]['number_id'] == 'dance2'
    assert dances[1]['minutes'] == 30


def test_time_analyzer_venue_slot_details():
    """Test that venue slot details are preserved."""
    def mock_time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    analyzer = TimeAnalyzer(mock_time_to_minutes)
    
    venue_schedule = [
        {'venue': 'Studio A', 'day': 'Monday', 'date': '1/20/26',
         'start': '6:00 PM', 'end': '8:00 PM'}
    ]
    
    result = analyzer.analyze([], venue_schedule)
    
    slot = result.venue_slots[0]
    assert slot['venue'] == 'Studio A'
    assert slot['day'] == 'Monday'
    assert slot['date'] == '1/20/26'
    assert slot['start'] == '6:00 PM'
    assert slot['end'] == '8:00 PM'
    assert slot['duration'] == 120