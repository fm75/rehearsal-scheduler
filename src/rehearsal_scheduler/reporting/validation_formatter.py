"""
Formatters for validation reports.

This module handles the display and output of validation results,
separated from the validation logic itself.
"""

import csv
from pathlib import Path
from typing import List, Optional, TextIO
import sys


class ValidationReportFormatter:
    """Formats validation results for display and file output."""
    
    def __init__(self, output_stream=None, error_stream=None):
        """
        Initialize formatter.
        
        Args:
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        self.output = output_stream or sys.stdout
        self.errors = error_stream or sys.stderr
    
    def print_header(self, source_name: str, constraint_column: str, id_column: str):
        """Print validation header."""
        self.output.write(f"Validating constraints from: {source_name}\n")
        self.output.write(f"Constraint column: '{constraint_column}', ID column: '{id_column}'\n")
        self.output.write("=" * 70 + "\n")
        self.output.flush()
    
    def print_valid_token(self, entity_id: str, token_num: int, token: str):
        """Print a valid token (for verbose mode)."""
        self.output.write(f"✓ {entity_id} [token {token_num}]: {token}\n")
        self.output.flush()
    
    def print_empty_row(self, entity_id: str):
        """Print empty constraint row (for verbose mode)."""
        self.output.write(f"  {entity_id}: (empty)\n")
        self.output.flush()
    
    def print_invalid_token(
        self, 
        entity_id: str, 
        row: int, 
        token_num: int, 
        token: str, 
        error: str
    ):
        """Print an invalid token error."""
        self.errors.write(f"\n❌ {entity_id} (row {row}, token {token_num}):\n")
        self.errors.write(f"   Token: '{token}'\n")
        self.errors.write(f"   {error}\n")
        self.errors.flush()
    
    def print_entity_separator(self, entity_id: str):
        """Print separator between entities."""
        self.errors.write(f"{30*'='} end of {entity_id} {30*'='}\n")
        self.errors.flush()
    
    def print_summary(self, stats, has_errors: bool):
        """Print validation summary."""
        self.output.write("\n" + "=" * 70 + "\n")
        self.output.write("SUMMARY\n")
        self.output.write("-" * 70 + "\n")
        self.output.write(f"Total entities:       {stats.total_rows}\n")
        self.output.write(f"Empty constraints:    {stats.empty_rows}\n")
        self.output.write(f"Total tokens:         {stats.total_tokens}\n")
        self.output.write(f"Valid tokens:         {stats.valid_tokens} ✓\n")
        
        if stats.invalid_tokens > 0:
            self.errors.write(f"Invalid tokens:       {stats.invalid_tokens} ❌\n")
        else:
            self.output.write(f"Invalid tokens:       {stats.invalid_tokens}\n")
        
        # Show success rate
        if stats.total_tokens > 0:
            status = "✓" if not has_errors else "⚠"
            self.output.write(
                f"Success rate:         {stats.success_rate:.1f}% {status}\n"
            )
        
        self.output.flush()
    
    def write_error_csv(
        self, 
        errors: List, 
        output_path: Path,
        message_stream=None
    ):
        """
        Write error report to CSV file.
        
        Args:
            errors: List of ValidationError objects
            output_path: Path to write CSV file
            message_stream: Stream to write success message (default: output_stream)
        """
        stream = message_stream or self.output
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=['entity_id', 'row', 'token_num', 'token', 'error']
                )
                writer.writeheader()
                
                for error in errors:
                    writer.writerow({
                        'entity_id': error.entity_id,
                        'row': error.row,
                        'token_num': error.token_num,
                        'token': error.token,
                        'error': error.error
                    })
            
            stream.write(f"\nError report written to: {output_path}\n")
            stream.flush()
        except Exception as e:
            self.errors.write(f"❌ Error writing output file: {e}\n")
            self.errors.flush()
            raise


class SingleTokenFormatter:
    """Formatter for single token validation."""
    
    def __init__(self, output_stream=None, error_stream=None):
        """
        Initialize formatter.
        
        Args:
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        self.output = output_stream or sys.stdout
        self.errors = error_stream or sys.stderr
    
    def print_result(self, token: str, result, error: Optional[str]):
        """
        Print validation result for a single token.
        
        Args:
            token: The token that was validated
            result: The parsed result (if valid)
            error: Error message (if invalid)
        """
        self.output.write(f"Token: {token}\n")
        self.output.write("-" * 50 + "\n")
        
        if error is None:
            self.output.write("✓ Valid!\n")
            self.output.write(f"Parsed as: {result}\n")
        else:
            self.output.write("❌ Invalid!\n")
            self.output.write(f"\n{error}\n")
        
        self.output.flush()