# tests/unit/test_grammar_time_of_date.py

import pytest
from datetime import date
from dataclasses import dataclass
from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import TimeOnDateConstraint


@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()


# A list of tuples: (input_string, expected_output_object_list)
VALID_CASES = [
   
    # --- Test Primitives: Time-on-Day Specs ---
    ("Feb 2 2026 after 5pm", [TimeOnDateConstraint(date(2026, 2, 2), 1700, 2359)]),
    ("Feb 2 2026 before 3pm", [TimeOnDateConstraint(date(2026, 2, 2), 0, 1500)]),
    ("Feb 2 2026 11am-3pm", [TimeOnDateConstraint(date(2026, 2, 2), 1100, 1500)]),
    
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

