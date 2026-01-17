# tests/unit/test_grammar_bad_date.py

import pytest
from datetime import date
from lark.exceptions import UnexpectedInput

from rehearsal_scheduler.grammar import constraint_parser  # Import your parser

@pytest.fixture
def parser():
    """Provides a configured Lark parser instance."""
    return constraint_parser(debug=True)
    
class TestDateGrammarErrors:
    """Test that date grammar provides helpful error messages."""
    
    def test_missing_year_slash_format(self):
        """Test error when year is missing in slash format."""
        with pytest.raises(UnexpectedInput) as exc_info:
            parser.parse("1/15")
        
        error = exc_info.value
        assert error.pos_in_stream is not None
        # Could check that YEAR is in expected tokens
    
    def test_missing_year_text_format(self):
        """Test error when year is missing in text format."""
        with pytest.raises(UnexpectedInput) as exc_info:
            constraint_parser.parse("Jan 15")
        
        error = exc_info.value
        assert error.pos_in_stream is not None
    
    def test_invalid_month_number(self):
        """Test error for invalid month number."""
        with pytest.raises((UnexpectedInput, ValueError)):
            constraint_parser.parse("13/15/26")
    
    def test_invalid_month_text(self):
        """Test error for invalid month abbreviation."""
        with pytest.raises(UnexpectedInput):
            constraint_parser.parse("XYZ 15 26")
    
    def test_invalid_day_for_month(self):
        """Test error for day that doesn't exist in month."""
        with pytest.raises(ValueError) as exc_info:
            constraint_parser.parse("Feb 29 2023")  # Not a leap year
        
        assert "Invalid date" in str(exc_info.value)
    
    def test_error_message_quality(self):
        """Test that error messages are informative."""
        try:
            constraint_parser.parse("Jan 2")
        except UnexpectedInput as e:
            # Error should indicate position and what was expected
            assert e.pos_in_stream is not None
            context = e.get_context("Jan 2")
            assert context is not None
            assert len(context) > 0