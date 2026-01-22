# test_check_constraints_sheets.py

import pytest
from rehearsal_scheduler.domain.constraint_validator import ConstraintValidator
from rehearsal_scheduler.grammar import validate_token

# This test doesn't need real Google credentials
def test_validate_records_with_sheet_data():
    """Test validation logic with simulated Google Sheets data."""
    # Simulate data from ws.get_all_records()
    records = [
        {'dancer_id': 'd_001', 'conflicts': 'W before 1 PM'},
        {'dancer_id': 'd_002', 'conflicts': 'invalid text here'},
        {'dancer_id': 'd_003', 'conflicts': ''},
        {'dancer_id': 'd_004', 'conflicts': 'M, Tu after 5 PM, Jan 20 26'},
    ]
    
    validator = ConstraintValidator(validate_token)
    errors, stats = validator.validate_records(
        records,
        id_column='dancer_id',
        constraint_column='conflicts'
    )
    
    assert stats.total_rows == 4
    assert stats.empty_rows == 1
    assert stats.valid_tokens == 4  # W, M, T after 5PM, Jan 20 26
    assert stats.invalid_tokens == 1  # "invalid text here"
    assert len(errors) == 1
    assert errors[0].entity_id == 'd_002'