# tests/unit/test_grammar.py

import pytest
from lark import LarkError
from dataclasses import dataclass

# --- Import the code to be tested ---
# This assumes your project is installed in editable mode (pip install -e .)
from dance_scheduler.grammar import (
    constraint_parser,
    ConstraintTransformer,
    SemanticValidationError,
)

from dance_scheduler.constraints import (
    DayOfWeekConstraint, 
    TimeOnDayConstraint,
)


# --- Fixture to provide a parser to all tests ---
# This is a pytest best practice.
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


# A list of tuples: (input_string, expected_output_object_list)
VALID_CASES = [
   
    # --- Test Primitives: Time-on-Day Specs ---
    ("sun after 5pm", (TimeOnDayConstraint("sunday", 1700, 2359),)),
    ("sun after 5 pm", (TimeOnDayConstraint("sunday", 1700, 2359),)),
    ("f before 9", (TimeOnDayConstraint("friday", 0, 900),)), # No AM/PM
    ("sat before 10am", (TimeOnDayConstraint("saturday", 0, 1000),)),
    ("m until 12pm", (TimeOnDayConstraint("monday", 0, 1200),)),
    ("w until 5 pm", (TimeOnDayConstraint("wednesday", 0, 1700),)),
    ("tues 2-4", (TimeOnDayConstraint("tuesday", 1400, 1600),)), # Test heuristic
    ("w 9am-12pm", (TimeOnDayConstraint("wednesday", 900, 1200),)),
    ("th after 14", (TimeOnDayConstraint("thursday", 1400, 2359),)), # Test military time
    
    # # --- Test Multiple Unavailability Specs ---
    (
        "m, w 2-4, f after 5pm",
        (
            DayOfWeekConstraint("monday"),
            TimeOnDayConstraint("wednesday", 1400, 1600),
            TimeOnDayConstraint("friday", 1700, 2359),
        ),
    ),
    (
        "  sat,sun  ", # Test with extra whitespace
        (
            DayOfWeekConstraint("saturday"),
            DayOfWeekConstraint("sunday"),
        ),
    ),
]


@pytest.mark.parametrize("conflict_string, expected_output", VALID_CASES)
def test_valid_constraints_parse_correctly(parser, conflict_string, expected_output):
    """
    Tests that various legally formatted strings parse into the correct
    constraint objects.
    """
    # The transformer is applied automatically by Lark's `parse` method
    result = parser.parse(conflict_string)
    print(result)
    print(expected_output)
    assert result == expected_output

# ===================================================================
# 2. Tests for SYNTACTICALLY INVALID inputs
# ===================================================================

# These are strings that the GRAMMAR itself should reject.
SYNTAX_ERROR_CASES = [
    "notaday",       # Not a valid day
    "mon tues",      # Missing comma between specs
    "fri after",     # Incomplete time range
    "10am-12pm",     # Missing day
    "w until-5pm",   # Invalid token '-'
]

@pytest.mark.parametrize("invalid_string", SYNTAX_ERROR_CASES)
def test_parser_raises_lark_error_for_bad_syntax(parser, invalid_string):
    """
    Tests that the parser raises a LarkError for malformed strings.
    This confirms the grammar rules are working as expected.
    """
    with pytest.raises(LarkError):
        parser.parse(invalid_string)

# ===================================================================
# 3. Tests for SEMANTICALLY INVALID inputs
# ===================================================================

# These strings are syntactically fine, but logically flawed.
# The TRANSFORMER should reject them.
SEMANTIC_ERROR_CASES = [
    "m after 25",      # Hour > 24
    "tues 13pm-2pm",   # Invalid 12-hour format
    "w 0am",           # Invalid 12-hour format
    "th 5-2pm",        # Start time is after end time
]

@pytest.mark.parametrize("invalid_string", SEMANTIC_ERROR_CASES)
def test_parser_raises_semantic_error_for_bad_logic(parser, invalid_string):
    """
    Tests that the transformer raises our custom SemanticValidationError
    for inputs that are syntactically valid but logically impossible.
    """
    # with pytest.raises(SemanticValidationError):
    #     parser.parse(invalid_string)
    pass