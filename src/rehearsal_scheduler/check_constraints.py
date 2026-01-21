# src/rehearsal_scheduler/check_constraints.py

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
import click

from rehearsal_scheduler.grammar import validate_token
from rehearsal_scheduler.models.intervals import (
    TimeInterval, 
    parse_time_string, 
    parse_date_string, 
    time_to_minutes
)
from rehearsal_scheduler.scheduling.conflicts import check_slot_conflicts


try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


@click.group()
def cli():
    """Rehearsal Scheduler constraint validation tools."""
    pass


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--column', '-c', default='conflicts', 
              help='Name of the column containing constraints')
@click.option('--id-column', '-i', default='dancer_id',
              help='Name of the column containing dancer IDs')
@click.option('--verbose', '-v', is_flag=True,
              help='Show all tokens including valid ones')
@click.option('--output', '-o', type=click.Path(),
              help='Write error report to CSV file')
def validate(csv_file, column, id_column, verbose, output):
    """Validate constraint tokens in a CSV file.
    
    Splits each constraint field on commas and validates each token separately.
    Reports errors by dancer ID and token for director cleanup.
    
    Example:
        check-constraints validate conflicts.csv
        check-constraints validate conflicts.csv -v
        check-constraints validate conflicts.csv -o errors.csv
    """
    from rehearsal_scheduler.persistence.base import DataSourceFactory
    from rehearsal_scheduler.domain.constraint_validator import ConstraintValidator
    from rehearsal_scheduler.reporting.validation_formatter import ValidationReportFormatter
    
    csv_path = Path(csv_file)
    
    try:
        # Create data source
        data_source = DataSourceFactory.create_csv(str(csv_path))
        
        # Load data
        records = data_source.read_records()
        
        # Create validator
        validator = ConstraintValidator(validate_token)
        
        # Create formatter  
        formatter = ValidationReportFormatter()
        
        # Print header
        formatter.print_header(
            data_source.get_source_name(),
            column,
            id_column
        )
        
        # Validate
        try:
            errors, stats = validator.validate_records(records, id_column, column)
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
        
        # Display results
        if verbose:
            # Re-process to show valid tokens
            for row_num, record in enumerate(records, start=2):
                entity_id = str(record.get(id_column, f"row_{row_num}")).strip()
                constraints_text = str(record.get(column, '')).strip()
                
                if not constraints_text:
                    formatter.print_empty_row(entity_id)
                    continue
                
                tokens = [t.strip() for t in constraints_text.split(',')]
                
                for token_num, token in enumerate(tokens, start=1):
                    if not token:
                        continue
                    
                    result, error = validator.validate_single_token(token)
                    
                    if error is None:
                        formatter.print_valid_token(entity_id, token_num, token)
                    else:
                        formatter.print_invalid_token(
                            entity_id, row_num, token_num, token, error
                        )
                
                formatter.print_entity_separator(entity_id)
        else:
            # Just show errors
            for error in errors:
                formatter.print_invalid_token(
                    error.entity_id,
                    error.row,
                    error.token_num,
                    error.token,
                    error.error
                )
                formatter.print_entity_separator(error.entity_id)
        
        # Print summary
        formatter.print_summary(stats, stats.has_errors)
        
        # Write error report if requested
        if output and errors:
            output_path = Path(output)
            formatter.write_error_csv(errors, output_path)
        
        # Exit with error code if there were failures
        if stats.has_errors:
            sys.exit(1)
    
    except FileNotFoundError:
        click.echo(f"❌ Error: File not found: {csv_path}", err=True)
        sys.exit(1)
    except csv.Error as e:
        click.echo(f"❌ Error reading CSV: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('sheet_url_or_id')
@click.option('--credentials', '-k', type=click.Path(exists=True),
              envvar='GOOGLE_CREDENTIALS_PATH',
              help='Path to Google service account JSON file')
@click.option('--worksheet', '-w', default='0',
              help='Worksheet index (0-based) or name (default: 0)')
@click.option('--column', '-c', default='conflicts', 
              help='Name of the column containing constraints')
@click.option('--id-column', '-i', default='dancer_id',
              help='Name of the column containing dancer IDs')
@click.option('--verbose', '-v', is_flag=True,
              help='Show all tokens including valid ones')
@click.option('--output', '-o', type=click.Path(),
              help='Write error report to CSV file')
def validate_sheet(sheet_url_or_id, credentials, worksheet, column, id_column, verbose, output):
    """Validate constraints from a Google Sheet.
    
    Requires Google Sheets API credentials (service account JSON).
    Share the sheet with the service account email found in the credentials file.
    
    Example:
        check-constraints validate-sheet "SHEET_ID" -k creds.json
        check-constraints validate-sheet "https://docs.google.com/..." -k creds.json
        check-constraints validate-sheet "SHEET_ID" -w "Conflicts" -v
    """
    from rehearsal_scheduler.persistence.base import DataSourceFactory
    from rehearsal_scheduler.domain.constraint_validator import ConstraintValidator
    from rehearsal_scheduler.reporting.validation_formatter import ValidationReportFormatter
    
    if not credentials:
        click.echo("❌ Error: Google credentials required", err=True)
        click.echo("Set GOOGLE_CREDENTIALS_PATH env var or use -k option", err=True)
        sys.exit(1)
    
    try:
        # Create data source
        data_source = DataSourceFactory.create_sheets(
            sheet_url_or_id,
            credentials,
            worksheet
        )
        
        # Load data
        try:
            records = data_source.read_records()
        except ImportError as e:
            click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            # Handle gspread exceptions
            error_type = type(e).__name__
            if 'SpreadsheetNotFound' in error_type:
                click.echo("❌ Error: Spreadsheet not found or not accessible", err=True)
                click.echo("Make sure the sheet is shared with the service account email", err=True)
            elif 'WorksheetNotFound' in error_type:
                click.echo(f"❌ Error: Worksheet '{worksheet}' not found", err=True)
            else:
                click.echo(f"❌ Error accessing Google Sheet: {e}", err=True)
                import traceback
                traceback.print_exc()
            sys.exit(1)
        
        # Create validator
        validator = ConstraintValidator(validate_token)
        
        # Create formatter
        formatter = ValidationReportFormatter()
        
        # Print header
        formatter.print_header(
            data_source.get_source_name(),
            column,
            id_column
        )
        
        # Validate
        try:
            errors, stats = validator.validate_records(records, id_column, column)
        except ValueError as e:
            click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
        
        # Display results (same as validate command)
        if verbose:
            for row_num, record in enumerate(records, start=2):
                entity_id = str(record.get(id_column, f"row_{row_num}")).strip()
                constraints_text = str(record.get(column, '')).strip()
                
                if not constraints_text:
                    formatter.print_empty_row(entity_id)
                    continue
                
                tokens = [t.strip() for t in constraints_text.split(',')]
                
                for token_num, token in enumerate(tokens, start=1):
                    if not token:
                        continue
                    
                    result, error = validator.validate_single_token(token)
                    
                    if error is None:
                        formatter.print_valid_token(entity_id, token_num, token)
                    else:
                        formatter.print_invalid_token(
                            entity_id, row_num, token_num, token, error
                        )
                
                formatter.print_entity_separator(entity_id)
        else:
            for error in errors:
                formatter.print_invalid_token(
                    error.entity_id,
                    error.row,
                    error.token_num,
                    error.token,
                    error.error
                )
                formatter.print_entity_separator(error.entity_id)
        
        # Print summary
        formatter.print_summary(stats, stats.has_errors)
        
        # Write error report if requested
        if output and errors:
            output_path = Path(output)
            formatter.write_error_csv(errors, output_path)
        
        # Exit with error code if there were failures
        if stats.has_errors:
            sys.exit(1)
    
    except FileNotFoundError:
        click.echo(f"❌ Error: Credentials file not found: {credentials}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('token_text')
def check(token_text):
    """Validate a single constraint token.
    
    Example:
        check-constraints check "W before 1 PM"
        check-constraints check "Jan 20 26"
        check-constraints check "T after 12:15"
    """
    from rehearsal_scheduler.domain.constraint_validator import ConstraintValidator
    from rehearsal_scheduler.reporting.validation_formatter import SingleTokenFormatter
    
    validator = ConstraintValidator(validate_token)
    result, error = validator.validate_single_token(token_text)
    
    formatter = SingleTokenFormatter()
    formatter.print_result(token_text, result, error)
    
    if error is not None:
        sys.exit(1)
# =============================================================================

import csv
from datetime import datetime
from pathlib import Path
import click

@cli.command()
@click.argument('time_requests_source')
@click.argument('venue_schedule_source')
@click.option('--sheet', '-s', is_flag=True,
              help='Sources are Google Sheet IDs instead of CSV files')
@click.option('--credentials', '-k', type=click.Path(exists=True),
              envvar='GOOGLE_CREDENTIALS_PATH',
              help='Path to Google service account JSON file (required if --sheet)')
@click.option('--requests-worksheet', default='0',
              help='Worksheet name/index for time requests (default: first sheet)')
@click.option('--venue-worksheet', default='0',
              help='Worksheet name/index for venue schedule (default: first sheet)')
@click.option('--use-allocated', is_flag=True,
              help='Use min_allocated column instead of min_requested (for post-allocation check)')
def analyze_time(time_requests_source, venue_schedule_source, sheet, credentials, 
                 requests_worksheet, venue_worksheet, use_allocated):
    """Analyze requested vs available rehearsal time.
    
    Calculates total time requested by rehearsal directors and compares it
    to available venue time slots.
    
    Examples:
        # From CSV files
        check-constraints analyze-time time_requests.csv venue_schedule.csv
        
        # From Google Sheets
        check-constraints analyze-time SHEET_ID1 SHEET_ID2 --sheet -k creds.json
    """
    from rehearsal_scheduler.persistence.base import DataSourceFactory
    from rehearsal_scheduler.domain.time_analyzer import TimeAnalyzer
    from rehearsal_scheduler.reporting.analysis_formatter import TimeAnalysisFormatter
    from rehearsal_scheduler.models.intervals import time_to_minutes
    
    if sheet:
        if not GSPREAD_AVAILABLE:
            click.echo("❌ Error: gspread library not installed", err=True)
            click.echo("Install with: pip install gspread google-auth", err=True)
            sys.exit(1)
        
        if not credentials:
            click.echo("❌ Error: Google credentials required with --sheet", err=True)
            sys.exit(1)
        
        # Load from Google Sheets
        try:
            source1 = DataSourceFactory.create_sheets(
                time_requests_source, credentials, requests_worksheet
            )
            source2 = DataSourceFactory.create_sheets(
                venue_schedule_source, credentials, venue_worksheet
            )
            time_requests = source1.read_records()
            venue_schedule = source2.read_records()
        except Exception as e:
            click.echo(f"❌ Error loading sheets: {e}", err=True)
            sys.exit(1)
    else:
        # Load from CSV
        try:
            source1 = DataSourceFactory.create_csv(time_requests_source)
            source2 = DataSourceFactory.create_csv(venue_schedule_source)
            time_requests = source1.read_records()
            venue_schedule = source2.read_records()
        except FileNotFoundError as e:
            click.echo(f"❌ Error: File not found: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error loading CSV: {e}", err=True)
            sys.exit(1)
    
    # Analyze
    analyzer = TimeAnalyzer(time_to_minutes)
    result = analyzer.analyze(time_requests, venue_schedule, use_allocated)
    
    # Display
    formatter = TimeAnalysisFormatter()
    formatter.display_analysis(result)
    
    # Exit with error if insufficient time
    if result.has_deficit:
        sys.exit(1)


# =============================================================================
# Add to check_constraints.py

@cli.command()
@click.argument('rhd_conflicts_source')
@click.argument('venue_schedule_source')
@click.argument('dance_map_source')
@click.option('--sheet', '-s', is_flag=True,
              help='Sources are Google Sheet IDs instead of CSV files')
@click.option('--credentials', '-k', type=click.Path(exists=True),
              envvar='GOOGLE_CREDENTIALS_PATH',
              help='Path to Google service account JSON file (required if --sheet)')
@click.option('--rhd-worksheet', default='0',
              help='Worksheet name/index for RD conflicts (default: first sheet)')
@click.option('--venue-worksheet', default='0',
              help='Worksheet name/index for venue schedule (default: first sheet)')
@click.option('--map-worksheet', default='0',
              help='Worksheet name/index for dance-director map (default: first sheet)')
@click.option('--output', '-o', type=click.Path(),
              help='Write conflict report to CSV file')
def conflict_report(rhd_conflicts_source, venue_schedule_source, dance_map_source,
                    sheet, credentials, rhd_worksheet, venue_worksheet, map_worksheet, output):
    """Generate a report showing RD availability conflicts with venue schedule.
    
    Shows which rehearsal directors are unavailable during scheduled venue times
    and which dances are affected, helping identify potential scheduling issues.
    
    Examples:
        # From CSV files
        check-constraints conflict-report rhd_conflicts.csv venue_schedule.csv dance_director_map.csv
        
        # From Google Sheets
        check-constraints conflict-report SHEET_ID SHEET_ID SHEET_ID --sheet -k creds.json
    """
    from rehearsal_scheduler.persistence.base import DataSourceFactory
    from rehearsal_scheduler.domain.conflict_analyzer import ConflictAnalyzer
    from rehearsal_scheduler.reporting.analysis_formatter import ConflictReportFormatter
    from rehearsal_scheduler.models.intervals import parse_date_string, parse_time_string, time_to_minutes
    
    if sheet:
        if not GSPREAD_AVAILABLE:
            click.echo("❌ Error: gspread library not installed", err=True)
            sys.exit(1)
        
        if not credentials:
            click.echo("❌ Error: Google credentials required with --sheet", err=True)
            sys.exit(1)
        
        # Load from Google Sheets
        try:
            source1 = DataSourceFactory.create_sheets(
                rhd_conflicts_source, credentials, rhd_worksheet
            )
            source2 = DataSourceFactory.create_sheets(
                venue_schedule_source, credentials, venue_worksheet
            )
            source3 = DataSourceFactory.create_sheets(
                dance_map_source, credentials, map_worksheet
            )
            rhd_conflicts = source1.read_records()
            venue_schedule = source2.read_records()
            dance_map = source3.read_records()
        except Exception as e:
            click.echo(f"❌ Error loading sheets: {e}", err=True)
            sys.exit(1)
    else:
        # Load from CSV
        try:
            source1 = DataSourceFactory.create_csv(rhd_conflicts_source)
            source2 = DataSourceFactory.create_csv(venue_schedule_source)
            source3 = DataSourceFactory.create_csv(dance_map_source)
            rhd_conflicts = source1.read_records()
            venue_schedule = source2.read_records()
            dance_map = source3.read_records()
        except FileNotFoundError as e:
            click.echo(f"❌ Error: File not found: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error loading CSV: {e}", err=True)
            sys.exit(1)
    
    # Helper to parse time
    def parse_time_helper(time_str):
        try:
            return parse_time_string(time_str)
        except Exception:
            return None
    
    # Analyze conflicts
    analyzer = ConflictAnalyzer(
        validate_token,
        check_slot_conflicts,
        parse_date_string,
        parse_time_helper,
        time_to_minutes
    )
    report = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)
    
    # Display
    formatter = ConflictReportFormatter()
    formatter.display_report(report)
    
    # Write to CSV if requested
    if output:
        formatter.write_csv(report, Path(output))
        

# =============================================================================
if __name__ == '__main__':
    cli()