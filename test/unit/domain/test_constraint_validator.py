"""
Tests for constraint validator domain logic.
"""

import pytest
from rehearsal_scheduler.domain.constraint_validator import (
    ConstraintValidator,
    ValidationStats,
    ValidationError
)


# Tests for ValidationStats dataclass

def test_validation_stats_success_rate_with_all_valid():
    """Test success rate when all tokens are valid."""
    stats = ValidationStats(
        total_rows=5,
        empty_rows=1,
        total_tokens=10,
        valid_tokens=10,
        invalid_tokens=0
    )
    
    assert stats.success_rate == 100.0
    assert not stats.has_errors


def test_validation_stats_success_rate_with_some_invalid():
    """Test success rate when some tokens are invalid."""
    stats = ValidationStats(
        total_rows=5,
        empty_rows=0,
        total_tokens=10,
        valid_tokens=7,
        invalid_tokens=3
    )
    
    assert stats.success_rate == 70.0
    assert stats.has_errors


def test_validation_stats_success_rate_with_zero_tokens():
    """Test success rate when there are no tokens."""
    stats = ValidationStats(
        total_rows=5,
        empty_rows=5,
        total_tokens=0,
        valid_tokens=0,
        invalid_tokens=0
    )
    
    assert stats.success_rate == 100.0
    assert not stats.has_errors


# Tests for ValidationError dataclass

def test_validation_error_creation():
    """Test creating a validation error."""
    error = ValidationError(
        entity_id='dancer_001',
        row=5,
        token_num=2,
        token='invalid token',
        error='Token is invalid'
    )
    
    assert error.entity_id == 'dancer_001'
    assert error.row == 5
    assert error.token_num == 2
    assert error.token == 'invalid token'
    assert error.error == 'Token is invalid'


# Tests for ConstraintValidator

def test_validator_all_valid_tokens():
    """Test validation when all tokens are valid."""
    def mock_validate(token):
        return (token, None)  # All tokens valid
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'Monday, Tuesday'},
        {'dancer_id': 'd2', 'conflicts': 'Wednesday'}
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert len(errors) == 0
    assert stats.total_rows == 2
    assert stats.total_tokens == 3
    assert stats.valid_tokens == 3
    assert stats.invalid_tokens == 0
    assert stats.success_rate == 100.0


def test_validator_with_invalid_tokens():
    """Test validation when some tokens are invalid."""
    def mock_validate(token):
        if token == 'bad':
            return (None, 'Invalid token')
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'Monday, bad'},
        {'dancer_id': 'd2', 'conflicts': 'Tuesday'}
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert len(errors) == 1
    assert errors[0].entity_id == 'd1'
    assert errors[0].token == 'bad'
    assert errors[0].error == 'Invalid token'
    assert stats.total_tokens == 3
    assert stats.valid_tokens == 2
    assert stats.invalid_tokens == 1


def test_validator_with_empty_constraints():
    """Test validation with empty constraint fields."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'Monday'},
        {'dancer_id': 'd2', 'conflicts': ''},
        {'dancer_id': 'd3', 'conflicts': 'Tuesday'}
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert len(errors) == 0
    assert stats.total_rows == 3
    assert stats.empty_rows == 1
    assert stats.total_tokens == 2


def test_validator_handles_trailing_commas():
    """Test that trailing commas don't create empty tokens."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'Monday, Tuesday,'}  # Trailing comma
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert stats.total_tokens == 2  # Should only count 2 tokens


def test_validator_flattens_multiline_errors():
    """Test that multiline errors are flattened."""
    def mock_validate(token):
        if token == 'bad':
            return (None, 'Error line 1\nError line 2')
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'bad'}
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert len(errors) == 1
    assert errors[0].error == 'Error line 1 | Error line 2'


def test_validator_missing_id_column_raises_error():
    """Test that missing ID column raises ValueError."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'name': 'd1', 'conflicts': 'Monday'}
    ]
    
    with pytest.raises(ValueError) as exc_info:
        validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert 'dancer_id' in str(exc_info.value)
    assert 'not found' in str(exc_info.value)


def test_validator_missing_constraint_column_raises_error():
    """Test that missing constraint column raises ValueError."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'name': 'Alice'}
    ]
    
    with pytest.raises(ValueError) as exc_info:
        validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert 'conflicts' in str(exc_info.value)
    assert 'not found' in str(exc_info.value)


def test_validator_empty_records():
    """Test validation with empty records list."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = []
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert len(errors) == 0
    assert stats.total_rows == 0
    assert stats.total_tokens == 0


def test_validator_single_token():
    """Test validating a single token."""
    def mock_validate(token):
        if token == 'valid':
            return ('parsed_valid', None)
        return (None, 'Invalid')
    
    validator = ConstraintValidator(mock_validate)
    
    # Valid token
    result, error = validator.validate_single_token('valid')
    assert result == 'parsed_valid'
    assert error is None
    
    # Invalid token
    result, error = validator.validate_single_token('invalid')
    assert result is None
    assert error == 'Invalid'


def test_validator_tracks_row_numbers_correctly():
    """Test that row numbers are tracked correctly (starting at 2)."""
    def mock_validate(token):
        if token == 'bad':
            return (None, 'Error')
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': 'good'},
        {'dancer_id': 'd2', 'conflicts': 'bad'},
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    # First record is row 2 (header is row 1)
    assert errors[0].row == 3  # Second record


def test_validator_handles_empty_entity_id():
    """Test handling of records with empty entity ID."""
    def mock_validate(token):
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': '', 'conflicts': 'Monday'}  # Empty dancer_id
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    # Should use fallback row_N format when ID is empty
    assert stats.total_rows == 1
    assert stats.valid_tokens == 1


def test_validator_strips_whitespace_from_tokens():
    """Test that whitespace is stripped from tokens."""
    tokens_seen = []
    
    def mock_validate(token):
        tokens_seen.append(token)
        return (token, None)
    
    validator = ConstraintValidator(mock_validate)
    
    records = [
        {'dancer_id': 'd1', 'conflicts': ' Monday , Tuesday '}
    ]
    
    errors, stats = validator.validate_records(records, 'dancer_id', 'conflicts')
    
    assert tokens_seen == ['Monday', 'Tuesday']