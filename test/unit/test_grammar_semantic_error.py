# tests/unit/test_grammar_semantic_error.py

from rehearsal_scheduler.grammar import validate_token
from rehearsal_scheduler.constraints import DateConstraint
from datetime import date


def test_missing_year_slash_format():
    expected = "Expected: "
    _, emsg = validate_token("m after 25")
    assert expected in emsg

def test_invalid_12_hour_format():
    expected = "Expected: "
    _, emsg = validate_token("tues 13pm-2pm")
    assert expected in emsg

def test_invalid_0_am():
    expected = "   ^"
    _, emsg = validate_token("w 0am")
    assert expected in emsg

def test_invalid_minutes():
    expected = "MINUTE"
    _, emsg = validate_token("th after 10:61 am")
    assert expected in emsg

def test_start_after_end_1():
    expected = "th 5-2pm: Start time 17:00:00 must be before end time 14:00:00."
    _, emsg = validate_token("th 5-2pm")
    assert emsg == expected

def test_start_after_end_2():
    expected = "th 11:30am-1100: Start time 11:30:00 must be before end time 11:00:00."
    _, emsg = validate_token("th 11:30am-1100")
    assert emsg == expected

def test_start_after_end_military():
    expected = "m 1500-1300: Start time 15:00:00 must be before end time 13:00:00."
    _, emsg = validate_token("m 1500-1300")
    assert emsg == expected

def test_start_date_after_end_date():
    expected = "jan 31 26-jan 2 26: Invalid range: end date 2026-01-02 is before start date 2026-01-31"
    _, emsg = validate_token("jan 31 26-jan 2 26")
    assert emsg == expected

def test_validate_token_with_good_token():
    expected = (DateConstraint(date(2026,1,2)),)
    result, emsg = validate_token("Jan 2 26")
    assert result == expected
