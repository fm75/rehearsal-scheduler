# tests/unit/test_grammar_date_constraints.py

from rehearsal_scheduler.grammar import validate_token
from rehearsal_scheduler.constraints import DateConstraint, DateRangeConstraint
from datetime import date


def test_validate_token_with_good_date_text():
    expected = (DateConstraint(date(2026,1,2)),)
    result, emsg = validate_token("Jan 2 26")
    assert result == expected
    
def test_validate_token_with_good_date_slash_yy():
    expected = (DateConstraint(date(2026,1,2)),)
    result, emsg = validate_token("1/2/26")
    assert result == expected
    
def test_validate_token_with_good_date_slash_yyyy():
    expected = (DateConstraint(date(2026,1,2)),)
    result, emsg = validate_token("1/2/2026")
    assert result == expected
    
def test_validate_token_with_good_date_range():
    expected = (DateRangeConstraint(date(2026,1,2), date(2026,1,5)),)
    result, emsg = validate_token("Jan 2 26-Jan 5 2026")
    assert result == expected