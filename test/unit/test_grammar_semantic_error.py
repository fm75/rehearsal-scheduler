# tests/unit/test_grammar_semantic_error.py

from rehearsal_scheduler.grammar import validate_token


def test_missing_year_slash_format():
    """Test error when year is missing in slash format."""
    expected = "Expected: "
    _, emsg = validate_token("m after 25")
    assert expected in emsg

def test_invalid_12_hour_format():
    """Test error when year is missing in slash format."""
    expected = "Expected: "
    _, emsg = validate_token("tues 13pm-2pm")
    assert expected in emsg

def test_invalid_0_am():
    """Test error when year is missing in slash format."""
    expected = "   ^"
    _, emsg = validate_token("w 0am")
    assert expected in emsg

def test_invalid_minutes():
    """Test error when year is missing in slash format."""
    expected = "MINUTE"
    _, emsg = validate_token("th after 10:61 am")
    assert expected in emsg

def test_start_after_end_1():
    """Test error when year is missing in slash format."""
    expected = "th 5-2pm: Start time 17:00:00 must be before end time 14:00:00."
    _, emsg = validate_token("th 5-2pm")
    assert emsg == expected

def test_start_after_end_2():
    """Test error when year is missing in slash format."""
    expected = "th 11:30am-1100: Start time 11:30:00 must be before end time 11:00:00."
    _, emsg = validate_token("th 11:30am-1100")
    assert emsg == expected

def test_start_after_end_military():
    """Test error when year is missing in slash format."""
    expected = "m 1500-1300: Start time 15:00:00 must be before end time 13:00:00."
    _, emsg = validate_token("m 1500-1300")
    assert emsg == expected
