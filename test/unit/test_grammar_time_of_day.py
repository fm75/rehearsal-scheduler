# tests/unit/test_grammar.py

import pytest
from dataclasses import dataclass
from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import TimeOnDayConstraint


@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()


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
    
    # # # --- Test Multiple Unavailability Specs ---
    # (
    #     "m, w 2-4, f after 5pm",
    #     (
    #         DayOfWeekConstraint("monday"),
    #         TimeOnDayConstraint("wednesday", 1400, 1600),
    #         TimeOnDayConstraint("friday", 1700, 2359),
    #     ),
    # ),
    # (
    #     "  sat,sun  ", # Test with extra whitespace
    #     (
    #         DayOfWeekConstraint("saturday"),
    #         DayOfWeekConstraint("sunday"),
    #     ),
    # ),
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

