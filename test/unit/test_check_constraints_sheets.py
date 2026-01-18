import pytest
# from unittest.mock import Mock, patch
from rehearsal_scheduler.check_constraints import validate_records

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
    
    error_records, stats = validate_records(
        records,
        id_column='dancer_id',
        column='conflicts',
        verbose=False,
        source_name='test'
    )
    
    assert stats['total_rows'] == 4
    assert stats['empty_rows'] == 1
    assert stats['valid_tokens'] == 4  # W, M, T after 5PM, Jan 20 26
    assert stats['invalid_tokens'] == 1  # "invalid text here"
    assert len(error_records) == 1
    assert error_records[0]['dancer_id'] == 'd_002'