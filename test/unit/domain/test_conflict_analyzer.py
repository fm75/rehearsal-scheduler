"""
Comprehensive test coverage for conflict_analyzer.py

Tests the actual ConflictAnalyzer class that analyzes RD (Rehearsal Director)
conflicts against venue schedules.
"""

import pytest
from datetime import time, date
from unittest.mock import Mock
from rehearsal_scheduler.domain.conflict_analyzer import ConflictAnalyzer, ConflictReport


# ============================================================================
# ConflictReport Tests
# ============================================================================

def test_conflict_report_creation():
    """Test creating a ConflictReport."""
    report = ConflictReport(
        conflicts=[{'rhd_id': 'RD001', 'venue': 'Studio A'}],
        rds_with_conflicts=['RD001'],
        total_conflicts=1,
        rd_dances={'RD001': ['Dance1']}
    )
    
    assert len(report.conflicts) == 1
    assert report.rds_with_conflicts == ['RD001']
    assert report.total_conflicts == 1
    assert report.rd_dances == {'RD001': ['Dance1']}


def test_has_conflicts_property_true():
    """Test has_conflicts property when conflicts exist."""
    report = ConflictReport(
        conflicts=[{'rhd_id': 'RD001'}],
        rds_with_conflicts=['RD001'],
        total_conflicts=1,
        rd_dances={}
    )
    
    assert report.has_conflicts is True


def test_has_conflicts_property_false():
    """Test has_conflicts property when no conflicts exist."""
    report = ConflictReport(
        conflicts=[],
        rds_with_conflicts=[],
        total_conflicts=0,
        rd_dances={}
    )
    
    assert report.has_conflicts is False


# ============================================================================
# ConflictAnalyzer Initialization Tests
# ============================================================================

def test_analyzer_initialization():
    """Test that ConflictAnalyzer initializes with all required functions."""
    validate_fn = Mock()
    check_conflicts_fn = Mock()
    parse_date_fn = Mock()
    parse_time_fn = Mock()
    time_to_minutes_fn = Mock()
    
    analyzer = ConflictAnalyzer(
        validate_fn,
        check_conflicts_fn,
        parse_date_fn,
        parse_time_fn,
        time_to_minutes_fn
    )
    
    assert analyzer.validate_token == validate_fn
    assert analyzer.check_slot_conflicts == check_conflicts_fn
    assert analyzer.parse_date == parse_date_fn
    assert analyzer.parse_time == parse_time_fn
    assert analyzer.time_to_minutes == time_to_minutes_fn


# ============================================================================
# Empty Input Tests
# ============================================================================

@pytest.fixture
def analyzer():
    """Create analyzer with mock functions for testing."""
    return ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 15)),
        parse_time_fn=Mock(return_value=time(14, 0)),
        time_to_minutes_fn=Mock(return_value=840)
    )


def test_analyze_all_empty_inputs(analyzer):
    """Test with all empty inputs."""
    result = analyzer.analyze(
        rhd_conflicts=[],
        venue_schedule=[],
        dance_map=[]
    )
    
    assert result.total_conflicts == 0
    assert result.rds_with_conflicts == []
    assert result.conflicts == []
    assert result.rd_dances == {}


def test_analyze_no_conflicts_specified(analyzer):
    """Test RDs with no conflicts specified."""
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': ''},
        {'rhd_id': 'RD002', 'conflicts': '   '}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert result.total_conflicts == 0
    assert result.rds_with_conflicts == []


def test_analyze_empty_venue_schedule(analyzer):
    """Test with conflicts specified but no venue schedule."""
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday, 14:00-16:00'}
    ]
    
    result = analyzer.analyze(rhd_conflicts, [], [])
    
    assert result.total_conflicts == 0
    assert result.rds_with_conflicts == []


# ============================================================================
# Dance Mapping Tests
# ============================================================================

def test_single_rd_single_dance(analyzer):
    """Test mapping one dance to one RD."""
    dance_map = [
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert result.rd_dances == {'RD001': ['Dance1']}


def test_single_rd_multiple_dances(analyzer):
    """Test mapping multiple dances to one RD."""
    dance_map = [
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance2', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance3', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert result.rd_dances == {'RD001': ['Dance1', 'Dance2', 'Dance3']}


def test_multiple_rds_multiple_dances(analyzer):
    """Test mapping dances to multiple RDs."""
    dance_map = [
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance2', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance3', 'rhd_id': 'RD002'},
        {'dance_id': 'Dance4', 'rhd_id': 'RD003'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert result.rd_dances == {
        'RD001': ['Dance1', 'Dance2'],
        'RD002': ['Dance3'],
        'RD003': ['Dance4']
    }


def test_empty_dance_ids_ignored(analyzer):
    """Test that empty dance IDs are ignored."""
    dance_map = [
        {'dance_id': '', 'rhd_id': 'RD001'},
        {'dance_id': '   ', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert result.rd_dances == {'RD001': ['Dance1']}


def test_missing_dance_id_key(analyzer):
    """Test handling missing dance_id key."""
    dance_map = [
        {'rhd_id': 'RD001'},  # Missing dance_id
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert result.rd_dances == {'RD001': ['Dance1']}


def test_whitespace_stripped_from_ids(analyzer):
    """Test that whitespace is stripped from IDs."""
    dance_map = [
        {'dance_id': '  Dance1  ', 'rhd_id': '  RD001  '},
        {'dance_id': 'Dance2', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze([], [], dance_map)
    
    assert 'RD001' in result.rd_dances
    assert 'Dance1' in result.rd_dances['RD001']


# ============================================================================
# Constraint Parsing Tests
# ============================================================================

def test_single_constraint_token():
    """Test parsing single constraint token."""
    validate_mock = Mock(return_value=('parsed_result', None))
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    validate_mock.assert_called_once_with('monday')


def test_multiple_constraint_tokens():
    """Test parsing multiple comma-separated constraint tokens."""
    validate_mock = Mock(return_value=('parsed_result', None))
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday, 14:00-16:00, 2025-01-20'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert validate_mock.call_count == 3


def test_invalid_constraint_token_skipped():
    """Test that invalid constraint tokens are skipped without crashing."""
    def validate_side_effect(token):
        if token == 'invalid':
            return (None, 'Invalid token')
        return ('parsed_result', None)
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(side_effect=validate_side_effect),
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday, invalid, 14:00-16:00'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    # Should not crash
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    assert result is not None


def test_empty_tokens_ignored():
    """Test that empty tokens from splitting are ignored."""
    validate_mock = Mock(return_value=('parsed_result', None))
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday,,, 14:00-16:00'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # Should only validate non-empty tokens
    assert validate_mock.call_count == 2


# ============================================================================
# Venue Schedule Parsing Tests
# ============================================================================

def test_parse_time_called_for_start_and_end():
    """Test that parse_time is called for both start and end times."""
    parse_time_mock = Mock(side_effect=[time(14, 0), time(16, 0)])
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=parse_time_mock,
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert parse_time_mock.call_count == 2
    parse_time_mock.assert_any_call('14:00')
    parse_time_mock.assert_any_call('16:00')


def test_invalid_start_time_skips_slot():
    """Test that slots with invalid start times are skipped."""
    check_conflicts_mock = Mock(return_value=[])
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=check_conflicts_mock,
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[None, time(16, 0)]),  # Invalid start
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': 'invalid',
        'end': '16:00'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # check_slot_conflicts should not be called
    check_conflicts_mock.assert_not_called()


def test_invalid_end_time_skips_slot():
    """Test that slots with invalid end times are skipped."""
    check_conflicts_mock = Mock(return_value=[])
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=check_conflicts_mock,
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), None]),  # Invalid end
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': 'invalid'
    }]
    
    analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # check_slot_conflicts should not be called
    check_conflicts_mock.assert_not_called()


def test_invalid_date_handled_gracefully():
    """Test that invalid dates are handled gracefully with None."""
    check_conflicts_mock = Mock(return_value=[])
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=check_conflicts_mock,
        parse_date_fn=Mock(side_effect=ValueError("Invalid date")),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': 'invalid-date',
        'start': '14:00',
        'end': '16:00'
    }]
    
    # Should not crash, slot_date will be None
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # Should still check conflicts with None date
    check_conflicts_mock.assert_called_once()


# ============================================================================
# Conflict Detection Tests
# ============================================================================

def test_no_conflicts_detected():
    """Test when check_slot_conflicts returns empty list."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'tuesday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert result.total_conflicts == 0
    assert result.rds_with_conflicts == []


def test_single_conflict_detected():
    """Test when one conflict is detected."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=['monday']),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    dance_map = [
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'}
    ]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    assert result.total_conflicts == 1
    assert result.rds_with_conflicts == ['RD001']
    assert len(result.conflicts) == 1
    
    conflict = result.conflicts[0]
    assert conflict['rhd_id'] == 'RD001'
    assert conflict['venue'] == 'Studio A'
    assert conflict['day'] == 'Monday'
    assert conflict['date'] == '2025-01-20'
    assert conflict['time_slot'] == '14:00 - 16:00'
    assert conflict['conflicting_constraints'] == ['monday']
    assert conflict['affected_dances'] == ['Dance1']


def test_multiple_conflicts_same_rd():
    """Test multiple conflicts for the same RD across different slots."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=['monday']),
        parse_date_fn=Mock(side_effect=[date(2025, 1, 20), date(2025, 1, 20)]),
        parse_time_fn=Mock(side_effect=[
            time(14, 0), time(16, 0),  # Slot 1
            time(18, 0), time(20, 0)   # Slot 2
        ]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [
        {
            'venue': 'Studio A',
            'day': 'Monday',
            'date': '2025-01-20',
            'start': '14:00',
            'end': '16:00'
        },
        {
            'venue': 'Studio B',
            'day': 'Monday',
            'date': '2025-01-20',
            'start': '18:00',
            'end': '20:00'
        }
    ]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert result.total_conflicts == 2
    assert result.rds_with_conflicts == ['RD001']


def test_multiple_rds_with_conflicts():
    """Test multiple RDs each with different conflicts."""
    def check_conflicts_side_effect(constraints, day, slot_date, start, end):
        for token, _ in constraints:
            if token == 'monday' and day == 'Monday':
                return ['monday']
            if token == 'tuesday' and day == 'Tuesday':
                return ['tuesday']
        return []
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts_side_effect),
        parse_date_fn=Mock(side_effect=[date(2025, 1, 20), date(2025, 1, 21)]),
        parse_time_fn=Mock(side_effect=[
            time(14, 0), time(16, 0),  # Monday slot
            time(14, 0), time(16, 0)   # Tuesday slot
        ]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'},
        {'rhd_id': 'RD002', 'conflicts': 'tuesday'}
    ]
    
    venue_schedule = [
        {
            'venue': 'Studio A',
            'day': 'Monday',
            'date': '2025-01-20',
            'start': '14:00',
            'end': '16:00'
        },
        {
            'venue': 'Studio B',
            'day': 'Tuesday',
            'date': '2025-01-21',
            'start': '14:00',
            'end': '16:00'
        }
    ]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert result.total_conflicts == 2
    assert sorted(result.rds_with_conflicts) == ['RD001', 'RD002']


def test_rd_without_associated_dances():
    """Test RD with conflicts but no associated dances in dance_map."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=['monday']),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    conflict = result.conflicts[0]
    assert conflict['affected_dances'] == []


def test_multiple_conflicting_constraints_same_slot():
    """Test when multiple constraints conflict with a single slot."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=['monday', '14:00-16:00']),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday, 14:00-16:00'}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    assert result.total_conflicts == 1
    conflict = result.conflicts[0]
    assert len(conflict['conflicting_constraints']) == 2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_missing_venue_field(analyzer):
    """Test handling missing venue field in schedule."""
    analyzer.parse_time = Mock(side_effect=[time(14, 0), time(16, 0)])
    analyzer.check_slot_conflicts = Mock(return_value=['monday'])
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'}
    ]
    
    venue_schedule = [{
        # Missing 'venue'
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # Should still process, venue will be empty string
    if result.conflicts:
        assert result.conflicts[0]['venue'] == ''


def test_missing_rhd_id_field(analyzer):
    """Test handling missing rhd_id field in conflicts."""
    rhd_conflicts = [
        {'conflicts': 'monday'}  # Missing rhd_id
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    # Should not crash
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    assert result is not None


def test_duplicate_rd_entries():
    """Test handling duplicate RD entries in conflicts list."""
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=['monday']),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday'},
        {'rhd_id': 'RD001', 'conflicts': 'tuesday'}  # Duplicate, different constraints
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # RD001 should appear once in rds_with_conflicts
    assert result.rds_with_conflicts.count('RD001') == 1


def test_very_long_constraints_string():
    """Test handling very long constraints strings."""
    validate_mock = Mock(return_value=('parsed', None))
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock(return_value=[]),
        parse_date_fn=Mock(return_value=date(2025, 1, 20)),
        parse_time_fn=Mock(side_effect=[time(14, 0), time(16, 0)]),
        time_to_minutes_fn=Mock()
    )
    
    # Create a very long constraints string
    long_constraints = ', '.join(['monday'] * 100)
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': long_constraints}
    ]
    
    venue_schedule = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    # Should not crash
    result = analyzer.analyze(rhd_conflicts, venue_schedule, [])
    
    # validate_token should be called 100 times
    assert validate_mock.call_count == 100


# ============================================================================
# Integration Tests
# ============================================================================

def test_realistic_scenario_mixed_conflicts():
    """Test realistic scenario with mixed conflicts and no-conflicts."""
    def check_conflicts_impl(constraints, day, slot_date, start, end):
        conflicts = []
        for token, _ in constraints:
            if token == 'monday' and day == 'Monday':
                conflicts.append('monday')
            if token == '14:00-16:00' and start == time(14, 0):
                conflicts.append('14:00-16:00')
        return conflicts
    
    analyzer = ConflictAnalyzer(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts_impl),
        parse_date_fn=Mock(side_effect=[date(2025, 1, 20), date(2025, 1, 21)]),
        parse_time_fn=Mock(side_effect=[
            time(14, 0), time(16, 0),  # Monday slot
            time(18, 0), time(20, 0),  # Tuesday slot
        ]),
        time_to_minutes_fn=Mock()
    )
    
    rhd_conflicts = [
        {'rhd_id': 'RD001', 'conflicts': 'monday, 14:00-16:00'},
        {'rhd_id': 'RD002', 'conflicts': 'friday'},
        {'rhd_id': 'RD003', 'conflicts': ''}
    ]
    
    venue_schedule = [
        {
            'venue': 'Studio A',
            'day': 'Monday',
            'date': '2025-01-20',
            'start': '14:00',
            'end': '16:00'
        },
        {
            'venue': 'Studio B',
            'day': 'Tuesday',
            'date': '2025-01-21',
            'start': '18:00',
            'end': '20:00'
        }
    ]
    
    dance_map = [
        {'dance_id': 'Dance1', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance2', 'rhd_id': 'RD001'},
        {'dance_id': 'Dance3', 'rhd_id': 'RD002'},
        {'dance_id': 'Dance4', 'rhd_id': 'RD003'}
    ]
    
    result = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    # Only RD001 should have conflicts
    assert result.total_conflicts == 1
    assert result.rds_with_conflicts == ['RD001']
    assert result.conflicts[0]['affected_dances'] == ['Dance1', 'Dance2']
    
    # All RDs should be in rd_dances map
    assert len(result.rd_dances) == 3