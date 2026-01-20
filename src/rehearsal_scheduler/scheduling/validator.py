"""Constraint validation and parsing."""

from typing import List, Tuple, Any
from rehearsal_scheduler.grammar import validate_token


def parse_constraints(conflict_text: str) -> List[Tuple[str, Any]]:
    """
    Parse constraint text into list of (token, parsed_result) tuples.
    
    Args:
        conflict_text: Comma-separated constraint tokens (e.g., "W before 1 PM, Jan 20 26")
        
    Returns:
        List of (original_token, parsed_constraint) tuples
        Empty list if conflict_text is empty
        
    Examples:
        >>> parse_constraints("W before 1 PM")
        [('W before 1 PM', <constraint object>)]
        
        >>> parse_constraints("")
        []
    """
    if not conflict_text:
        return []
    
    tokens = [t.strip() for t in conflict_text.split(',')]
    parsed = []
    
    for token in tokens:
        if token:
            result, error = validate_token(token)
            if not error:
                parsed.append((token, result))
    
    return parsed