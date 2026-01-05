# tests/unit/test_grammar.py

import pytest
from lark import LarkError
from rehearsal_scheduler.grammar import constraint_parser

@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()

# ===================================================================
# Tests for SYNTACTICALLY INVALID inputs
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
