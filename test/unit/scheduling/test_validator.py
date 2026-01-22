"""
Tests for scheduling/validator.py
"""

import pytest
from unittest.mock import Mock, patch
from rehearsal_scheduler.scheduling.validator import parse_constraints


def test_parse_constraints_empty_string():
    """Test with empty constraint string."""
    result = parse_constraints("")
    
    assert result == []


def test_parse_constraints_none_empty():
    """Test with whitespace-only string."""
    result = parse_constraints("   ")
    
    # Should strip to empty and return []
    assert result == []


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_single_valid_token(mock_validate):
    """Test parsing single valid token."""
    mock_validate.return_value = ('parsed_constraint', None)
    
    result = parse_constraints("monday")
    
    assert len(result) == 1
    assert result[0] == ('monday', 'parsed_constraint')
    mock_validate.assert_called_once_with('monday')


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_multiple_tokens(mock_validate):
    """Test parsing multiple comma-separated tokens."""
    mock_validate.return_value = ('parsed', None)
    
    result = parse_constraints("monday, tuesday, 14:00-16:00")
    
    assert len(result) == 3
    assert result[0][0] == 'monday'
    assert result[1][0] == 'tuesday'
    assert result[2][0] == '14:00-16:00'
    assert mock_validate.call_count == 3


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_skips_invalid_tokens(mock_validate):
    """Test that invalid tokens are skipped."""
    def validate_side_effect(token):
        if token == 'invalid':
            return (None, 'Error message')
        return ('parsed', None)
    
    mock_validate.side_effect = validate_side_effect
    
    result = parse_constraints("monday, invalid, tuesday")
    
    # Should only have 2 results (invalid skipped)
    assert len(result) == 2
    assert result[0][0] == 'monday'
    assert result[1][0] == 'tuesday'


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_strips_whitespace(mock_validate):
    """Test that whitespace is stripped from tokens."""
    mock_validate.return_value = ('parsed', None)
    
    result = parse_constraints("  monday  ,  tuesday  ")
    
    mock_validate.assert_any_call('monday')
    mock_validate.assert_any_call('tuesday')


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_skips_empty_tokens(mock_validate):
    """Test that empty tokens from splitting are skipped."""
    mock_validate.return_value = ('parsed', None)
    
    result = parse_constraints("monday, , , tuesday")
    
    # Should only validate non-empty tokens
    assert len(result) == 2
    assert mock_validate.call_count == 2


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_preserves_token_text(mock_validate):
    """Test that original token text is preserved in result."""
    mock_validate.return_value = ('parsed_obj', None)
    
    result = parse_constraints("W before 1 PM")
    
    assert result[0][0] == 'W before 1 PM'
    assert result[0][1] == 'parsed_obj'


@patch('rehearsal_scheduler.scheduling.validator.validate_token')
def test_parse_constraints_complex_tokens(mock_validate):
    """Test with complex constraint tokens."""
    mock_validate.return_value = ('parsed', None)
    
    result = parse_constraints("M, Tu after 5 PM, Jan 20-26, 14:00-16:00")
    
    assert len(result) == 4
    assert result[0][0] == 'M'
    assert result[1][0] == 'Tu after 5 PM'
    assert result[2][0] == 'Jan 20-26'
    assert result[3][0] == '14:00-16:00'