# tests/unit/test_grammar_semantic_error.py

import pytest
from lark import LarkError
from rehearsal_scheduler.grammar import (
    constraint_parser,
    SemanticValidationError,
)

@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser()


# ===================================================================
# Tests for SEMANTICALLY INVALID inputs
# These strings are syntactically fine, but logically flawed.
# The TRANSFORMER should reject them.# ===================================================================

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
    with pytest.raises(SemanticValidationError):
        parser.parse(invalid_string)
