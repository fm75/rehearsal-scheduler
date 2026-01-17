# tests/unit/test_grammar_bad_date.py

from rehearsal_scheduler.grammar import validate_token


def test_missing_year_slash_format():
    """Test error when year is missing in slash format."""
    expected = "1/15\n  ^\nExpected: {'SLASH'}"
    _, emsg = validate_token("1/15")
    assert emsg == expected

def test_missing_year_text_format():
    """Test error when year is missing in text format."""
    expected = "Jan 15\n    ^\nExpected: {'YEAR'}"
    _, emsg = validate_token("Jan 15")
    assert emsg == expected

def test_invalid_month_number():
    """Test error for invalid month number."""
    expected = "13/15/26\n ^\nExpected: {'SLASH'}"
    _, emsg = validate_token("13/15/26")
    assert emsg == expected

def test_invalid_month_text():
    """Test error for invalid month abbreviation."""
    expected = "Expected one of "
    _, emsg = validate_token("XYZ 15 26")
    assert expected in emsg

def test_invalid_day_for_month():
    """Test error for day that doesn't exist in month."""
    expected = "Feb 29 2023: Invalid date: day is out of range for month"
    _, emsg = validate_token("Feb 29 2023")
    assert emsg == expected
