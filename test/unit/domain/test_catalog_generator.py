"""
Comprehensive test coverage for catalog_generator.py

Tests the CatalogGenerator that analyzes which dances can be scheduled
in each venue slot based on RD and cast availability.
"""

import pytest
from unittest.mock import Mock
from rehearsal_scheduler.domain.catalog_generator import (
    CatalogGenerator,
    DanceAvailability,
    VenueCatalogSlot,
    VenueCatalog
)


# ============================================================================
# DanceAvailability Tests
# ============================================================================

def test_dance_availability_creation():
    """Test creating a DanceAvailability instance."""
    availability = DanceAvailability(
        dance_id='Dance1',
        rhd_id='RD001',
        cast_size=5,
        attendance_pct=100.0,
        conflicted_count=0,
        conflicted_dancers=[]
    )
    
    assert availability.dance_id == 'Dance1'
    assert availability.rhd_id == 'RD001'
    assert availability.cast_size == 5
    assert availability.attendance_pct == 100.0
    assert availability.conflicted_count == 0
    assert availability.conflicted_dancers == []


def test_dance_availability_conflicted_dancers_defaults_to_empty_list():
    """Test that conflicted_dancers defaults to empty list if not provided."""
    availability = DanceAvailability(
        dance_id='Dance1',
        rhd_id='RD001',
        cast_size=5,
        attendance_pct=80.0
    )
    
    assert availability.conflicted_dancers == []


def test_dance_availability_with_conflicts():
    """Test DanceAvailability with conflicted dancers."""
    availability = DanceAvailability(
        dance_id='Dance1',
        rhd_id='RD001',
        cast_size=5,
        attendance_pct=60.0,
        conflicted_count=2,
        conflicted_dancers=['Dancer1', 'Dancer2']
    )
    
    assert availability.conflicted_count == 2
    assert availability.conflicted_dancers == ['Dancer1', 'Dancer2']


# ============================================================================
# VenueCatalogSlot Tests
# ============================================================================

def test_venue_catalog_slot_creation():
    """Test creating a VenueCatalogSlot instance."""
    slot = VenueCatalogSlot(
        venue='Studio A',
        day='Monday',
        date='2025-01-20',
        start='14:00',
        end='16:00',
        conflict_free_dances=[],
        cast_conflict_dances=[],
        rd_blocked_dances=[]
    )
    
    assert slot.venue == 'Studio A'
    assert slot.day == 'Monday'
    assert slot.date == '2025-01-20'
    assert slot.start == '14:00'
    assert slot.end == '16:00'
    assert slot.conflict_free_dances == []
    assert slot.cast_conflict_dances == []
    assert slot.rd_blocked_dances == []


def test_venue_catalog_slot_with_dances():
    """Test VenueCatalogSlot with categorized dances."""
    conflict_free = DanceAvailability('Dance1', 'RD001', 5, 100.0)
    cast_conflict = DanceAvailability('Dance2', 'RD002', 4, 75.0, 1, ['Dancer1'])
    rd_blocked = DanceAvailability('Dance3', 'RD003', 6, 0.0, 0, ['RD unavailable'])
    
    slot = VenueCatalogSlot(
        venue='Studio A',
        day='Monday',
        date='2025-01-20',
        start='14:00',
        end='16:00',
        conflict_free_dances=[conflict_free],
        cast_conflict_dances=[cast_conflict],
        rd_blocked_dances=[rd_blocked]
    )
    
    assert len(slot.conflict_free_dances) == 1
    assert len(slot.cast_conflict_dances) == 1
    assert len(slot.rd_blocked_dances) == 1


# ============================================================================
# VenueCatalog Tests
# ============================================================================

def test_venue_catalog_creation():
    """Test creating a VenueCatalog."""
    slot1 = VenueCatalogSlot('Studio A', 'Monday', '2025-01-20', '14:00', '16:00', [], [], [])
    slot2 = VenueCatalogSlot('Studio B', 'Tuesday', '2025-01-21', '18:00', '20:00', [], [], [])
    
    catalog = VenueCatalog(slots=[slot1, slot2])
    
    assert len(catalog.slots) == 2
    assert catalog.total_slots == 2


def test_venue_catalog_empty():
    """Test VenueCatalog with no slots."""
    catalog = VenueCatalog(slots=[])
    
    assert catalog.total_slots == 0


def test_venue_catalog_total_slots_property():
    """Test that total_slots property works correctly."""
    slots = [
        VenueCatalogSlot('Studio A', 'Monday', '2025-01-20', '14:00', '16:00', [], [], [])
        for _ in range(5)
    ]
    catalog = VenueCatalog(slots=slots)
    
    assert catalog.total_slots == 5


# ============================================================================
# CatalogGenerator Initialization Tests
# ============================================================================

def test_catalog_generator_initialization():
    """Test CatalogGenerator initializes with required functions."""
    validate_fn = Mock()
    check_conflicts_fn = Mock()
    
    generator = CatalogGenerator(validate_fn, check_conflicts_fn)
    
    assert generator.validate_token == validate_fn
    assert generator.check_slot_conflicts == check_conflicts_fn


# ============================================================================
# Constraint Parsing Tests (_parse_constraints)
# ============================================================================

def test_parse_constraints_empty_string():
    """Test parsing empty constraint string."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(),
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('')
    
    assert result == []


def test_parse_constraints_single_valid_token():
    """Test parsing single valid constraint token."""
    validate_mock = Mock(return_value=('parsed_result', None))
    
    generator = CatalogGenerator(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('monday')
    
    assert result == ['parsed_result']
    validate_mock.assert_called_once_with('monday')


def test_parse_constraints_multiple_valid_tokens():
    """Test parsing multiple valid constraint tokens."""
    validate_mock = Mock(return_value=('parsed_result', None))
    
    generator = CatalogGenerator(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('monday, 14:00-16:00, 2025-01-20')
    
    assert len(result) == 3
    assert validate_mock.call_count == 3


def test_parse_constraints_with_invalid_token():
    """Test that invalid tokens are skipped."""
    def validate_side_effect(token):
        if token == 'invalid':
            return (None, 'Error: invalid token')
        return (token, None)
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(side_effect=validate_side_effect),
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('monday, invalid, tuesday')
    
    assert len(result) == 2
    assert 'monday' in result
    assert 'tuesday' in result


def test_parse_constraints_empty_tokens_ignored():
    """Test that empty tokens are ignored."""
    validate_mock = Mock(return_value=('parsed', None))
    
    generator = CatalogGenerator(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('monday,  , , tuesday')
    
    assert len(result) == 2
    assert validate_mock.call_count == 2


def test_parse_constraints_whitespace_stripped():
    """Test that whitespace is stripped from tokens."""
    validate_mock = Mock(return_value=('parsed', None))
    
    generator = CatalogGenerator(
        validate_token_fn=validate_mock,
        check_slot_conflicts_fn=Mock()
    )
    
    result = generator._parse_constraints('  monday  ,  tuesday  ')
    
    validate_mock.assert_any_call('monday')
    validate_mock.assert_any_call('tuesday')


# ============================================================================
# Empty Input Tests (generate method)
# ============================================================================

@pytest.fixture
def generator():
    """Create generator with mock functions."""
    return CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )


def test_generate_empty_inputs(generator):
    """Test generate with all empty inputs."""
    result = generator.generate(
        dance_cast={},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={},
        venue_slots=[]
    )
    
    assert isinstance(result, VenueCatalog)
    assert result.total_slots == 0


def test_generate_no_dances(generator):
    """Test generate with venue slots but no dances."""
    venue_slots = [
        {
            'venue': 'Studio A',
            'day': 'Monday',
            'date': '2025-01-20',
            'start': '14:00',
            'end': '16:00'
        }
    ]
    
    result = generator.generate(
        dance_cast={},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={},
        venue_slots=venue_slots
    )
    
    assert result.total_slots == 1
    assert len(result.slots[0].conflict_free_dances) == 0
    assert len(result.slots[0].cast_conflict_dances) == 0
    assert len(result.slots[0].rd_blocked_dances) == 0


def test_generate_no_venue_slots(generator):
    """Test generate with dances but no venue slots."""
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1', 'Dancer2']},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=[]
    )
    
    assert result.total_slots == 0


# ============================================================================
# Conflict-Free Dance Tests
# ============================================================================

def test_generate_single_conflict_free_dance():
    """Test dance with no conflicts appears in conflict_free_dances."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)  # No conflicts
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1', 'Dancer2']},
        dancer_constraints={'Dancer1': '', 'Dancer2': ''},
        rhd_constraints={'RD001': ''},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    assert len(slot.conflict_free_dances) == 1
    assert len(slot.cast_conflict_dances) == 0
    assert len(slot.rd_blocked_dances) == 0
    
    dance = slot.conflict_free_dances[0]
    assert dance.dance_id == 'Dance1'
    assert dance.rhd_id == 'RD001'
    assert dance.cast_size == 2
    assert dance.attendance_pct == 100.0
    assert dance.conflicted_count == 0
    assert dance.conflicted_dancers == []


def test_generate_multiple_conflict_free_dances():
    """Test multiple dances with no conflicts."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={
            'Dance1': ['Dancer1'],
            'Dance2': ['Dancer2'],
            'Dance3': ['Dancer3']
        },
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={'Dance1': 'RD001', 'Dance2': 'RD002', 'Dance3': 'RD003'},
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    assert len(slot.conflict_free_dances) == 3


# ============================================================================
# RD Blocked Dance Tests
# ============================================================================

def test_generate_rd_blocked_dance():
    """Test dance blocked by RD conflict appears in rd_blocked_dances."""
    def check_conflicts(constraints, slot):
        # RD has conflict, cast doesn't
        return len(constraints) > 0
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1']},
        dancer_constraints={'Dancer1': ''},
        rhd_constraints={'RD001': 'monday'},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    assert len(slot.rd_blocked_dances) == 1
    assert len(slot.conflict_free_dances) == 0
    assert len(slot.cast_conflict_dances) == 0
    
    dance = slot.rd_blocked_dances[0]
    assert dance.dance_id == 'Dance1'
    assert dance.attendance_pct == 0
    assert dance.conflicted_dancers == ['RD unavailable']


def test_generate_multiple_rd_blocked_dances():
    """Test multiple dances blocked by RD conflicts."""
    def check_conflicts(constraints, slot):
        return len(constraints) > 0
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={
            'Dance1': ['Dancer1'],
            'Dance2': ['Dancer2']
        },
        dancer_constraints={},
        rhd_constraints={'RD001': 'monday', 'RD002': 'monday'},
        dance_to_rd={'Dance1': 'RD001', 'Dance2': 'RD002'},
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    assert len(slot.rd_blocked_dances) == 2


# ============================================================================
# Cast Conflict Dance Tests
# ============================================================================

def test_generate_cast_conflict_dance():
    """Test dance with cast conflicts appears in cast_conflict_dances."""
    call_count = [0]
    
    def check_conflicts(constraints, slot):
        call_count[0] += 1
        # First call is RD (no conflict), second is cast member (conflict)
        return call_count[0] == 2 and len(constraints) > 0
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1', 'Dancer2']},
        dancer_constraints={'Dancer1': 'monday', 'Dancer2': ''},
        rhd_constraints={'RD001': ''},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    assert len(slot.cast_conflict_dances) == 1
    assert len(slot.conflict_free_dances) == 0
    assert len(slot.rd_blocked_dances) == 0
    
    dance = slot.cast_conflict_dances[0]
    assert dance.dance_id == 'Dance1'
    assert dance.cast_size == 2
    assert dance.conflicted_count == 1
    assert dance.attendance_pct == 50.0
    assert 'Dancer1' in dance.conflicted_dancers


def test_generate_cast_conflict_attendance_calculation():
    """Test attendance percentage calculation with cast conflicts."""
    call_count = [0]
    
    def check_conflicts(constraints, slot):
        call_count[0] += 1
        # RD ok, then 2 of 5 dancers conflict
        if call_count[0] == 1:
            return False
        return call_count[0] in [2, 3] and len(constraints) > 0
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['D1', 'D2', 'D3', 'D4', 'D5']},
        dancer_constraints={
            'D1': 'monday',
            'D2': 'monday',
            'D3': '',
            'D4': '',
            'D5': ''
        },
        rhd_constraints={'RD001': ''},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    dance = result.slots[0].cast_conflict_dances[0]
    assert dance.cast_size == 5
    assert dance.conflicted_count == 2
    assert dance.attendance_pct == 60.0  # 3 out of 5


def test_generate_cast_conflicts_sorted_by_attendance():
    """Test that cast conflict dances are sorted by attendance percentage."""
    call_count = [0]
    
    def check_conflicts(constraints, slot):
        call_count[0] += 1
        # RD checks (1,3,5) = False, dancer checks vary
        if call_count[0] in [1, 3, 5]:
            return False
        # Dance1: 1 conflict (50%), Dance2: 2 conflicts (33%), Dance3: no conflicts
        if call_count[0] == 2:  # Dance1 Dancer1
            return len(constraints) > 0
        if call_count[0] in [4, 6]:  # Dance2 Dancer1 and Dancer2
            return len(constraints) > 0
        return False
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={
            'Dance1': ['D1', 'D2'],  # 50% attendance
            'Dance2': ['D3', 'D4', 'D5']  # 33% attendance
        },
        dancer_constraints={
            'D1': 'monday',
            'D2': '',
            'D3': 'monday',
            'D4': 'monday',
            'D5': ''
        },
        rhd_constraints={'RD001': '', 'RD002': ''},
        dance_to_rd={'Dance1': 'RD001', 'Dance2': 'RD002'},
        venue_slots=venue_slots
    )
    
    cast_conflicts = result.slots[0].cast_conflict_dances
    # Should be sorted highest attendance first
    assert cast_conflicts[0].attendance_pct > cast_conflicts[1].attendance_pct


# ============================================================================
# Multiple Slot Tests
# ============================================================================

def test_generate_multiple_venue_slots():
    """Test generating catalog for multiple venue slots."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [
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
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1']},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    assert result.total_slots == 2
    assert result.slots[0].venue == 'Studio A'
    assert result.slots[1].venue == 'Studio B'


def test_generate_different_conflicts_per_slot():
    """Test that same dance can have different availability per slot."""
    
    def check_conflicts(constraints, slot):
        # Check if RD has 'tuesday' constraint and slot is on Tuesday
        if len(constraints) > 0 and slot.get('day') == 'Tuesday':
            return True
        return False
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [
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
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1']},
        dancer_constraints={'Dancer1': ''},
        rhd_constraints={'RD001': 'tuesday'},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    # Monday: conflict free, Tuesday: RD blocked
    assert len(result.slots[0].conflict_free_dances) == 1
    assert len(result.slots[1].rd_blocked_dances) == 1


# ============================================================================
# Edge Cases
# ============================================================================

def test_generate_empty_cast():
    """Test dance with empty cast."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': []},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    dance = result.slots[0].conflict_free_dances[0]
    assert dance.cast_size == 0
    assert dance.attendance_pct == 100.0  # Division by zero handled


def test_generate_missing_dance_to_rd_mapping():
    """Test dance without RD mapping uses 'Unknown'."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1']},
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={},  # Missing Dance1
        venue_slots=venue_slots
    )
    
    dance = result.slots[0].conflict_free_dances[0]
    assert dance.rhd_id == 'Unknown'


def test_generate_missing_dancer_constraints():
    """Test dancer without constraints in dict."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1', 'Dancer2']},
        dancer_constraints={'Dancer1': 'monday'},  # Dancer2 missing
        rhd_constraints={},
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    # Should not crash, Dancer2 treated as no constraints
    assert result.total_slots == 1


def test_generate_missing_rhd_constraints():
    """Test RD without constraints in dict."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={'Dance1': ['Dancer1']},
        dancer_constraints={},
        rhd_constraints={},  # RD001 missing
        dance_to_rd={'Dance1': 'RD001'},
        venue_slots=venue_slots
    )
    
    # Should not crash, RD treated as no constraints
    assert len(result.slots[0].conflict_free_dances) == 1


def test_generate_dances_sorted_alphabetically():
    """Test that dances are processed in sorted order."""
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(return_value=False)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={
            'Dance_Z': ['Dancer1'],
            'Dance_A': ['Dancer2'],
            'Dance_M': ['Dancer3']
        },
        dancer_constraints={},
        rhd_constraints={},
        dance_to_rd={
            'Dance_Z': 'RD001',
            'Dance_A': 'RD002',
            'Dance_M': 'RD003'
        },
        venue_slots=venue_slots
    )
    
    dances = result.slots[0].conflict_free_dances
    assert dances[0].dance_id == 'Dance_A'
    assert dances[1].dance_id == 'Dance_M'
    assert dances[2].dance_id == 'Dance_Z'


# ============================================================================
# Integration Tests
# ============================================================================

def test_generate_realistic_scenario():
    """Test realistic scenario with mixed availability."""
    
    def check_conflicts(constraints, slot):
        # If no constraints, no conflict
        if len(constraints) == 0:
            return False
        # Otherwise, simulate a conflict based on having constraints
        # This is a simple mock - just checks if constraints exist
        return True
    
    generator = CatalogGenerator(
        validate_token_fn=Mock(return_value=('parsed', None)),
        check_slot_conflicts_fn=Mock(side_effect=check_conflicts)
    )
    
    venue_slots = [{
        'venue': 'Studio A',
        'day': 'Monday',
        'date': '2025-01-20',
        'start': '14:00',
        'end': '16:00'
    }]
    
    result = generator.generate(
        dance_cast={
            'Dance1': ['Dancer1', 'Dancer2'],
            'Dance2': ['Dancer3'],
            'Dance3': ['Dancer4', 'Dancer5', 'Dancer6']
        },
        dancer_constraints={
            'Dancer1': 'monday',  # Has constraint
            'Dancer2': '',        # No constraint
            'Dancer3': ''         # No constraint
            # Dancer4, 5, 6 not in dict = no constraints
        },
        rhd_constraints={
            'RD1': '',            # No constraint
            'RD2': 'monday',      # Has constraint -> RD blocked
            'RD3': ''             # No constraint
        },
        dance_to_rd={
            'Dance1': 'RD1',
            'Dance2': 'RD2',
            'Dance3': 'RD3'
        },
        venue_slots=venue_slots
    )
    
    slot = result.slots[0]
    # Dance1: RD ok, but 1 cast conflict -> cast_conflict_dances
    # Dance2: RD blocked -> rd_blocked_dances
    # Dance3: RD ok, no cast conflicts -> conflict_free_dances
    assert len(slot.conflict_free_dances) == 1  # Dance3
    assert len(slot.cast_conflict_dances) == 1   # Dance1
    assert len(slot.rd_blocked_dances) == 1      # Dance2
    
    assert slot.conflict_free_dances[0].dance_id == 'Dance3'
    assert slot.cast_conflict_dances[0].dance_id == 'Dance1'
    assert slot.rd_blocked_dances[0].dance_id == 'Dance2'