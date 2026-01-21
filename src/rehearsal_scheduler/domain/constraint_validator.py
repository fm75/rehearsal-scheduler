"""
Constraint validation domain logic.

This module contains the business logic for validating constraint tokens,
separated from CLI and data loading concerns.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationStats:
    """Statistics from constraint validation."""
    total_rows: int
    empty_rows: int
    total_tokens: int
    valid_tokens: int
    invalid_tokens: int
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tokens == 0:
            return 100.0
        return (self.valid_tokens / self.total_tokens) * 100.0
    
    @property
    def has_errors(self) -> bool:
        """Check if there were any validation errors."""
        return self.invalid_tokens > 0


@dataclass
class ValidationError:
    """Record of a validation error."""
    entity_id: str  # dancer_id or rhd_id
    row: int
    token_num: int
    token: str
    error: str


class ConstraintValidator:
    """Validates constraint tokens using the grammar."""
    
    def __init__(self, validate_token_fn):
        """
        Initialize validator.
        
        Args:
            validate_token_fn: Function to validate a single token.
                Should return (result, error) tuple.
        """
        self.validate_token = validate_token_fn
    
    def validate_records(
        self,
        records: List[Dict[str, Any]],
        id_column: str,
        constraint_column: str
    ) -> Tuple[List[ValidationError], ValidationStats]:
        """
        Validate constraint tokens from records.
        
        Args:
            records: List of dicts with constraint data
            id_column: Name of column containing entity IDs
            constraint_column: Name of column containing constraints
            
        Returns:
            Tuple of (error_list, stats)
            
        Raises:
            ValueError: If required columns are not found
        """
        # Validate column existence
        if records and id_column not in records[0]:
            available = ', '.join(records[0].keys()) if records else 'none'
            raise ValueError(
                f"Column '{id_column}' not found. Available columns: {available}"
            )
        
        if records and constraint_column not in records[0]:
            available = ', '.join(records[0].keys()) if records else 'none'
            raise ValueError(
                f"Column '{constraint_column}' not found. Available columns: {available}"
            )
        
        # Initialize counters
        total_rows = 0
        total_tokens = 0
        valid_tokens = 0
        invalid_tokens = 0
        empty_rows = 0
        errors = []
        
        # Process each record
        for row_num, record in enumerate(records, start=2):  # Start at 2 (header is row 1)
            total_rows += 1
            entity_id = str(record.get(id_column, f"row_{row_num}")).strip()
            constraints_text = str(record.get(constraint_column, '')).strip()
            
            # Skip empty constraints
            if not constraints_text:
                empty_rows += 1
                continue
            
            # Split on commas to get individual tokens
            tokens = [t.strip() for t in constraints_text.split(',')]
            
            for token_num, token in enumerate(tokens, start=1):
                if not token:  # Skip empty tokens from trailing commas
                    continue
                
                total_tokens += 1
                result, error = self.validate_token(token)
                
                if error is None:
                    valid_tokens += 1
                else:
                    invalid_tokens += 1
                    errors.append(ValidationError(
                        entity_id=entity_id,
                        row=row_num,
                        token_num=token_num,
                        token=token,
                        error=error.replace('\n', ' | ')  # Flatten multiline errors
                    ))
        
        stats = ValidationStats(
            total_rows=total_rows,
            empty_rows=empty_rows,
            total_tokens=total_tokens,
            valid_tokens=valid_tokens,
            invalid_tokens=invalid_tokens
        )
        
        return errors, stats
    
    def validate_single_token(self, token: str) -> Tuple[Any, Optional[str]]:
        """
        Validate a single constraint token.
        
        Args:
            token: The constraint token to validate
            
        Returns:
            Tuple of (parsed_result, error_message)
            error_message is None if valid
        """
        return self.validate_token(token)