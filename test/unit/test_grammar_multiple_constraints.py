# tests/unit/test_grammar_multiple_constraints.py

import pytest
from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint, 
    TimeOnDayConstraint,
)

@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()


# A list of tuples: (input_string, expected_output_object_list)
MULTIPLE_CONSTRAINTS = [
 
    # # --- Test Multiple Unavailability Specs ---
    (
        "m, w 2-4, f after 5pm",
        [
            DayOfWeekConstraint("monday"),
            TimeOnDayConstraint("wednesday", 1400, 1600),
            TimeOnDayConstraint("friday", 1700, 2359),
        ],
    ),
    (
        "  sat,sun  ", # Test with extra whitespace
        [
            DayOfWeekConstraint("saturday"),
            DayOfWeekConstraint("sunday"),
        ],
    ),
]


@pytest.mark.parametrize("conflict_string, expected_output", MULTIPLE_CONSTRAINTS)
def test_valid_constraints_parse_correctly(parser, conflict_string, expected_output):
    result = parser.parse(conflict_string)
    print(result)
    print(expected_output)
    assert result == expected_output

