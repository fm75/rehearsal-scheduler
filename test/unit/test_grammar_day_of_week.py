# tests/unit/test_grammar_day_of_week.py

import pytest
from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import DayOfWeekConstraint 

@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()

# ===================================================================
# 1. Tests for VALID inputs ("Happy Path")
# ===================================================================
MONDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("MONDAY"), ("MON"), ("MO"), ("M "),
    ("Monday"), ("Mon"), ("Mo"), ("M"), 
    ("monday"), ("mon"), ("mo"), ("m"), 
]
@pytest.mark.parametrize("conflict_string", MONDAY)
def test_day_of_week_monday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("monday"),)

TUESDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("TUESDAY"), ("TUES"), ("TU"), 
    ("Tuesday"), ("Tues"), ("Tu"),  
    ("tuesday"), ("tues"), ("tu"),
]
@pytest.mark.parametrize("conflict_string", TUESDAY)
def test_day_of_week_tuesday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("tuesday"),)

WEDNESDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("WEDNESDAY"), ("WED"), ("WE"), 
    ("Wednesday"), ("Wed"), ("We"), ("W"), 
    ("wednesday"), ("wed"), ("wed"), ("w"), 
]
@pytest.mark.parametrize("conflict_string", WEDNESDAY)
def test_day_of_week_wednesday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("wednesday"),)

THURSDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("THURSDAY"), ("THURS"), ("TH"), 
    ("Thursday"), ("Thurs"), ("Th"),  
    ("thursday"), ("thurs"), ("th"),
]
@pytest.mark.parametrize("conflict_string", THURSDAY)
def test_day_of_week_thursday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("thursday"),)


SATURDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("SATURDAY"), ("SAT"), ("SA"), 
    ("Saturday"), ("Sat"), ("Sa"),  
    ("saturday"), ("sat"), ("sa"),
]
@pytest.mark.parametrize("conflict_string", SATURDAY)
def test_day_of_week_saturday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("saturday"),)

SUNDAY = [
    # --- Test Primitives: Simple Day Specs ---
    ("SUNDAY"), ("SUN"), ("SU"), 
    ("Sunday"), ("Sun"), ("Su"),  
    ("sunday"), ("sun"), ("su"),
]
@pytest.mark.parametrize("conflict_string", SUNDAY)
def test_day_of_week_sunday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("sunday"),)

WEEKEND = [
    ("Sa, Su"),
]
@pytest.mark.parametrize("conflict_string", WEEKEND)
def test_day_of_week_sunday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("saturday"),DayOfWeekConstraint("sunday"),)
    
WEEKDAYS = [
    ("M,Tu,W,Th,F"),
]
@pytest.mark.parametrize("conflict_string", WEEKDAYS)
def test_day_of_week_sunday(parser, conflict_string):
    assert parser.parse(conflict_string) == (DayOfWeekConstraint("monday"),
                                             DayOfWeekConstraint("tuesday"),
                                             DayOfWeekConstraint("wednesday"),
                                             DayOfWeekConstraint("thursday"),
                                             DayOfWeekConstraint("friday"),
                                            )

# 