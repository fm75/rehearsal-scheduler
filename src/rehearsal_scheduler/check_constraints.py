# src/rehearsal_scheduler/check_constraints.py

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
import click

from rehearsal_scheduler.grammar import validate_token

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


def validate_records(
    records: List[Dict[str, Any]], 
    id_column: str, 
    column: str, 
    verbose: bool,
    source_name: str = "data"
) -> tuple:
    """
    Shared validation logic for both CSV and Google Sheets.
    
    Args:
        records: List of dicts with constraint data
        id_column: Name of column containing dancer IDs
        column: Name of column containing constraints
        verbose: Whether to show valid tokens
        source_name: Name of data source for display
        
    Returns:
        Tuple of (error_records, stats_dict)
    """
    click.echo(f"Validating constraints from: {source_name}")
    click.echo(f"Constraint column: '{column}', ID column: '{id_column}'")
    click.echo("=" * 70)
    
    total_rows = 0
    total_tokens = 0
    valid_tokens = 0
    invalid_tokens = 0
    empty_rows = 0
    error_records = []
    
    # Check if required columns exist
    if records and id_column not in records[0]:
        available = ', '.join(records[0].keys()) if records else 'none'
        click.echo(f"❌ Error: Column '{id_column}' not found", err=True)
        click.echo(f"Available columns: {available}", err=True)
        return [], None
        
    if records and column not in records[0]:
        available = ', '.join(records[0].keys()) if records else 'none'
        click.echo(f"❌ Error: Column '{column}' not found", err=True)
        click.echo(f"Available columns: {available}", err=True)
        return [], None
    
    for row_num, record in enumerate(records, start=2):  # Start at 2 (header is row 1)
        total_rows += 1
        dancer_id = str(record.get(id_column, f"row_{row_num}")).strip()
        conflicts_text = str(record.get(column, '')).strip()
        
        # Skip empty constraints
        if not conflicts_text:
            empty_rows += 1
            if verbose:
                click.echo(f"  {dancer_id}: (empty)")
            continue
        
        # Split on commas to get individual tokens
        tokens = [t.strip() for t in conflicts_text.split(',')]
        
        for token_num, token in enumerate(tokens, start=1):
            if not token:  # Skip empty tokens from trailing commas
                continue
                
            total_tokens += 1
            result, error = validate_token(token)
            
            if error is None:
                # Valid token
                valid_tokens += 1
                if verbose:
                    click.echo(f"✓ {dancer_id} [token {token_num}]: {token}")
            else:
                # Invalid token
                invalid_tokens += 1
                click.echo(f"\n❌ {dancer_id} (row {row_num}, token {token_num}):", err=True)
                click.echo(f"   Token: '{token}'", err=True)
                click.echo(f"   {error}", err=True)
                
                # Store for CSV output
                error_records.append({
                    'dancer_id': dancer_id,
                    'row': row_num,
                    'token_num': token_num,
                    'token': token,
                    'error': error.replace('\n', ' | ')  # Flatten multiline errors
                })
        click.echo(f"{30*'='} end of {dancer_id} {30*'='}", err=True) 
    
    # Calculate stats
    stats = {
        'total_rows': total_rows,
        'empty_rows': empty_rows,
        'total_tokens': total_tokens,
        'valid_tokens': valid_tokens,
        'invalid_tokens': invalid_tokens
    }
    
    return error_records, stats


def print_summary(stats: Dict[str, int], error_records: List[Dict], output_path: Path = None):
    """Print validation summary and optionally write error report."""
    click.echo("\n" + "=" * 70)
    click.echo("SUMMARY")
    click.echo("-" * 70)
    click.echo(f"Total dancers:        {stats['total_rows']}")
    click.echo(f"Empty constraints:    {stats['empty_rows']}")
    click.echo(f"Total tokens:         {stats['total_tokens']}")
    click.echo(f"Valid tokens:         {stats['valid_tokens']} ✓")
    
    if stats['invalid_tokens'] > 0:
        click.echo(f"Invalid tokens:       {stats['invalid_tokens']} ❌", err=True)
    else:
        click.echo(f"Invalid tokens:       {stats['invalid_tokens']}")
    
    # Show success rate
    if stats['total_tokens'] > 0:
        success_rate = (stats['valid_tokens'] / stats['total_tokens']) * 100
        status = "✓" if stats['invalid_tokens'] == 0 else "⚠"
        click.echo(f"Success rate:         {success_rate:.1f}% {status}")
    
    # Write error report if requested
    if output_path and error_records:
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['dancer_id', 'row', 'token_num', 'token', 'error'])
                writer.writeheader()
                writer.writerows(error_records)
            click.echo(f"\nError report written to: {output_path}")
        except Exception as e:
            click.echo(f"❌ Error writing output file: {e}", err=True)


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
    csv_path = Path(csv_file)
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        error_records, stats = validate_records(
            records, 
            id_column, 
            column, 
            verbose,
            source_name=csv_path.name
        )
        
        if stats is None:  # Column not found
            sys.exit(1)
        
        output_path = Path(output) if output else None
        print_summary(stats, error_records, output_path)
        
        # Exit with error code if there were failures
        if stats['invalid_tokens'] > 0:
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
    if not GSPREAD_AVAILABLE:
        click.echo("❌ Error: gspread library not installed", err=True)
        click.echo("Install with: pip install gspread google-auth", err=True)
        sys.exit(1)
    
    if not credentials:
        click.echo("❌ Error: Google credentials required", err=True)
        click.echo("Set GOOGLE_CREDENTIALS_PATH env var or use -k option", err=True)
        sys.exit(1)
    
    try:
        # Authenticate
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        creds = Credentials.from_service_account_file(credentials, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open sheet
        if sheet_url_or_id.startswith('http'):
            sheet = client.open_by_url(sheet_url_or_id)
        else:
            sheet = client.open_by_key(sheet_url_or_id)
        
        # Get worksheet
        try:
            if isinstance(worksheet, int):
                ws = sheet.get_worksheet(worksheet)
            elif worksheet.isdigit():
                ws = sheet.get_worksheet(int(worksheet))
            else:
                ws = sheet.worksheet(worksheet)
        except (gspread.exceptions.WorksheetNotFound, IndexError):
            click.echo(f"❌ Error: Worksheet '{worksheet}' not found", err=True)
            available = [w.title for w in sheet.worksheets()]
            click.echo(f"Available worksheets: {', '.join(available)}", err=True)
            sys.exit(1)
        
        # Get all records as dicts
        records = ws.get_all_records()
        
        source_name = f"{sheet.title} / {ws.title}"
        
        error_records, stats = validate_records(
            records, 
            id_column, 
            column, 
            verbose,
            source_name=source_name
        )
        
        if stats is None:  # Column not found
            sys.exit(1)
        
        output_path = Path(output) if output else None
        print_summary(stats, error_records, output_path)
        
        # Exit with error code if there were failures
        if stats['invalid_tokens'] > 0:
            sys.exit(1)
        
    except gspread.exceptions.SpreadsheetNotFound:
        click.echo("❌ Error: Spreadsheet not found or not accessible", err=True)
        click.echo("Make sure the sheet is shared with the service account email", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(f"❌ Error: Credentials file not found: {credentials}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error accessing Google Sheet: {e}", err=True)
        import traceback
        traceback.print_exc()
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
    result, error = validate_token(token_text)
    
    click.echo(f"Token: {token_text}")
    click.echo("-" * 50)
    
    if error is None:
        click.echo("✓ Valid!")
        click.echo(f"Parsed as: {result}")
    else:
        click.echo("❌ Invalid!")
        click.echo(f"\n{error}")
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
    if sheet:
        if not GSPREAD_AVAILABLE:
            click.echo("❌ Error: gspread library not installed", err=True)
            click.echo("Install with: pip install gspread google-auth", err=True)
            sys.exit(1)
        
        if not credentials:
            click.echo("❌ Error: Google credentials required with --sheet", err=True)
            sys.exit(1)
        
        # Load from Google Sheets
        time_requests = load_from_sheet(
            time_requests_source, credentials, requests_worksheet
        )
        venue_schedule = load_from_sheet(
            venue_schedule_source, credentials, venue_worksheet
        )
    else:
        # Load from CSV
        time_requests = load_from_csv(time_requests_source)
        venue_schedule = load_from_csv(venue_schedule_source)
    
    # Analyze
    analysis = analyze_time_requirements(time_requests, venue_schedule)
    
    # Display results
    display_time_analysis(analysis)
    
    # Exit with error if insufficient time
    if analysis['deficit'] > 0:
        sys.exit(1)


def load_from_csv(filepath):
    """Load data from CSV file."""
    path = Path(filepath)
    if not path.exists():
        click.echo(f"❌ Error: File not found: {filepath}", err=True)
        sys.exit(1)
    
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_from_sheet(sheet_id, credentials_path, worksheet):
    """Load data from Google Sheet."""
    from google.oauth2.service_account import Credentials
    import gspread
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        if worksheet.isdigit():
            ws = sheet.get_worksheet(int(worksheet))
        else:
            ws = sheet.worksheet(worksheet)
        
        return ws.get_all_records()
    
    except Exception as e:
        click.echo(f"❌ Error loading sheet {sheet_id}: {e}", err=True)
        sys.exit(1)


def parse_time(time_str):
    """Parse time string like '11:00 AM' to datetime.time."""
    try:
        return datetime.strptime(time_str.strip(), '%I:%M %p').time()
    except ValueError:
        # Try without AM/PM
        try:
            return datetime.strptime(time_str.strip(), '%H:%M').time()
        except ValueError:
            click.echo(f"⚠ Warning: Could not parse time '{time_str}'", err=True)
            return None


def analyze_time_requirements(time_requests, venue_schedule, use_allocated=False):
    """Calculate requested or allocated vs available time."""
    
    # Choose which column to use
    time_column = 'min_allocated' if use_allocated else 'min_requested'
    
    # Calculate total requested time
    total_requested = 0
    requests_by_director = {}
    missing_requests = []
    
    for row in time_requests:
        number_id = row.get('number_id', '')
        rhd_id = row.get('rhd_id', '')
        minutes_str = str(row.get(time_column, '')).strip()
        
        if minutes_str and minutes_str != '':
            try:
                minutes = float(minutes_str)
                total_requested += minutes
                
                if rhd_id not in requests_by_director:
                    requests_by_director[rhd_id] = {'total': 0, 'dances': []}
                requests_by_director[rhd_id]['total'] += minutes
                requests_by_director[rhd_id]['dances'].append({
                    'number_id': number_id,
                    'minutes': minutes
                })
            except ValueError:
                click.echo(f"⚠ Warning: Invalid minutes for {number_id}: '{minutes_str}'", err=True)
        else:
            missing_requests.append(number_id)
    
    # Calculate total available time
    total_available = 0
    venue_slots = []
    
    for row in venue_schedule:
        venue = row.get('venue', '')
        day = row.get('day', '')
        date = row.get('date', '')
        start_str = row.get('start', '')
        end_str = row.get('end', '')
        
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)
        
        if start_time and end_time:
            # Calculate duration in minutes
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            duration = end_mins - start_mins
            
            total_available += duration
            venue_slots.append({
                'venue': venue,
                'day': day,
                'date': date,
                'start': start_str,
                'end': end_str,
                'duration': duration
            })
    
    # Calculate deficit/surplus
    deficit = total_requested - total_available
    
    return {
        'total_requested': total_requested,
        'total_available': total_available,
        'deficit': deficit,
        'requests_by_director': requests_by_director,
        'missing_requests': missing_requests,
        'venue_slots': venue_slots
    }


def display_time_analysis(analysis):
    """Display formatted time analysis."""
    click.echo("=" * 70)
    click.echo("REHEARSAL TIME ANALYSIS")
    click.echo("=" * 70)
    
    # Requested time
    click.echo("\n📋 TIME REQUESTED")
    click.echo("-" * 70)
    
    for rhd_id, data in sorted(analysis['requests_by_director'].items()):
        click.echo(f"\n{rhd_id}: {data['total']:.0f} minutes ({data['total']/60:.1f} hours)")
        for dance in data['dances']:
            click.echo(f"  • {dance['number_id']}: {dance['minutes']:.0f} min")
    
    if analysis['missing_requests']:
        click.echo(f"\n⚠ Missing time requests: {', '.join(analysis['missing_requests'])}")
    
    click.echo(f"\n{'TOTAL REQUESTED:':.<50} {analysis['total_requested']:.0f} min ({analysis['total_requested']/60:.1f} hrs)")
    
    # Available time
    click.echo("\n\n🏢 VENUE AVAILABILITY")
    click.echo("-" * 70)
    
    for slot in analysis['venue_slots']:
        click.echo(f"\n{slot['venue']} - {slot['day']}, {slot['date']}")
        click.echo(f"  {slot['start']} - {slot['end']}")
        click.echo(f"  Duration: {slot['duration']} min ({slot['duration']/60:.1f} hrs)")
    
    click.echo(f"\n{'TOTAL AVAILABLE:':.<50} {analysis['total_available']:.0f} min ({analysis['total_available']/60:.1f} hrs)")
    
    # Comparison
    click.echo("\n\n⚖️  COMPARISON")
    click.echo("=" * 70)
    
    if analysis['deficit'] > 0:
        click.echo(f"❌ INSUFFICIENT TIME: {analysis['deficit']:.0f} min ({analysis['deficit']/60:.1f} hrs) SHORT", err=True)
        click.echo(f"\nYou need {analysis['deficit']:.0f} more minutes of venue time.", err=True)
        click.echo("Options:", err=True)
        click.echo("  1. Add more venue time slots", err=True)
        click.echo("  2. Reduce requested rehearsal times", err=True)
        click.echo("  3. Poll for additional venue availability", err=True)
    elif analysis['deficit'] < 0:
        surplus = abs(analysis['deficit'])
        click.echo(f"✓ SURPLUS: {surplus:.0f} min ({surplus/60:.1f} hrs) extra time available")
        utilization = (analysis['total_requested'] / analysis['total_available']) * 100
        click.echo(f"Venue utilization: {utilization:.1f}%")
    else:
        click.echo("✓ PERFECT MATCH: Requested time equals available time")
        click.echo("⚠ Warning: No buffer time for adjustments")
    
    click.echo("=" * 70)

# =============================================================================
# Add to check_constraints.py

@cli.command()
@click.argument('rhd_conflicts_source')
@click.argument('venue_schedule_source')
@click.option('--sheet', '-s', is_flag=True,
              help='Sources are Google Sheet IDs instead of CSV files')
@click.option('--credentials', '-k', type=click.Path(exists=True),
              envvar='GOOGLE_CREDENTIALS_PATH',
              help='Path to Google service account JSON file (required if --sheet)')
@click.option('--rhd-worksheet', default='0',
              help='Worksheet name/index for RD conflicts (default: first sheet)')
@click.option('--venue-worksheet', default='0',
              help='Worksheet name/index for venue schedule (default: first sheet)')
@click.option('--output', '-o', type=click.Path(),
              help='Write conflict report to CSV file')
def conflict_report(rhd_conflicts_source, venue_schedule_source, sheet, credentials,
                    rhd_worksheet, venue_worksheet, output):
    """Generate a report showing RD availability conflicts with venue schedule.
    
    Shows which rehearsal directors are unavailable during scheduled venue times,
    helping the director identify potential scheduling issues before assignment.
    
    Examples:
        # From CSV files
        check-constraints conflict-report rhd_conflicts.csv venue_schedule.csv
        
        # From Google Sheets with output file
        check-constraints conflict-report SHEET_ID1 SHEET_ID2 --sheet -k creds.json -o conflicts.csv
    """
    if sheet:
        if not GSPREAD_AVAILABLE:
            click.echo("❌ Error: gspread library not installed", err=True)
            sys.exit(1)
        
        if not credentials:
            click.echo("❌ Error: Google credentials required with --sheet", err=True)
            sys.exit(1)
        
        rhd_conflicts = load_from_sheet(rhd_conflicts_source, credentials, rhd_worksheet)
        venue_schedule = load_from_sheet(venue_schedule_source, credentials, venue_worksheet)
    else:
        rhd_conflicts = load_from_csv(rhd_conflicts_source)
        venue_schedule = load_from_csv(venue_schedule_source)
    
    # Generate conflict report
    report = generate_conflict_report(rhd_conflicts, venue_schedule)
    
    # Display
    display_conflict_report(report)
    
    # Write to CSV if requested
    if output:
        write_conflict_report_csv(report, output)


def generate_conflict_report(rhd_conflicts, venue_schedule):
    """Analyze RD conflicts against venue schedule."""
    from rehearsal_scheduler.grammar import validate_token
    from datetime import datetime
    
    conflicts_found = []
    rds_with_conflicts = set()
    
    # Parse each RD's constraints
    rd_constraints = {}
    for row in rhd_conflicts:
        rhd_id = row.get('rhd_id', '').strip()
        conflicts_text = row.get('conflicts', '').strip()
        
        if not conflicts_text:
            rd_constraints[rhd_id] = []
            continue
        
        # Parse constraint tokens
        tokens = [t.strip() for t in conflicts_text.split(',')]
        parsed_constraints = []
        
        for token in tokens:
            if not token:
                continue
            result, error = validate_token(token)
            if error:
                click.echo(f"⚠ Warning: Invalid constraint for {rhd_id}: {token}", err=True)
            else:
                parsed_constraints.append((token, result))
        
        rd_constraints[rhd_id] = parsed_constraints
    
    # Check each venue slot against each RD
    for venue_row in venue_schedule:
        venue = venue_row.get('venue', '')
        day = venue_row.get('day', '')
        date_str = venue_row.get('date', '')
        start_str = venue_row.get('start', '')
        end_str = venue_row.get('end', '')
        
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)
        
        if not start_time or not end_time:
            continue
        
        # Parse the date
        try:
            slot_date = datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            try:
                slot_date = datetime.strptime(date_str, '%m/%d/%y').date()
            except ValueError:
                click.echo(f"⚠ Warning: Could not parse date '{date_str}'", err=True)
                slot_date = None
        
        # Check each RD against this slot
        for rhd_id, constraints in rd_constraints.items():
            if not constraints:
                continue
            
            slot_conflicts = check_slot_conflicts(
                constraints, day, slot_date, start_time, end_time
            )
            
            if slot_conflicts:
                rds_with_conflicts.add(rhd_id)
                conflicts_found.append({
                    'rhd_id': rhd_id,
                    'venue': venue,
                    'day': day,
                    'date': date_str,
                    'time_slot': f"{start_str} - {end_str}",
                    'conflicting_constraints': slot_conflicts
                })
    
    return {
        'conflicts': conflicts_found,
        'rds_with_conflicts': sorted(rds_with_conflicts),
        'total_conflicts': len(conflicts_found)
    }


def check_slot_conflicts(constraints, slot_day, slot_date, slot_start, slot_end):
    """Check if RD constraints conflict with a specific time slot."""
    from rehearsal_scheduler.constraints import (
        DayOfWeekConstraint, TimeOnDayConstraint, 
        DateConstraint, DateRangeConstraint
    )
    from datetime import time
    
    conflicting = []
    slot_day_lower = slot_day.lower()
    
    for token_text, parsed_result in constraints:
        # Handle tuple of constraints
        if isinstance(parsed_result, tuple):
            constraint_list = parsed_result
        else:
            constraint_list = [parsed_result]
        
        for constraint in constraint_list:
            conflict = False
            
            if isinstance(constraint, DayOfWeekConstraint):
                # RD unavailable all day on this day of week
                if constraint.day_of_week == slot_day_lower:
                    conflict = True
            
            elif isinstance(constraint, TimeOnDayConstraint):
                # RD unavailable during specific time on this day
                if constraint.day_of_week == slot_day_lower:
                    # Convert constraint times to time objects
                    constraint_start = time(constraint.start_time // 100, 
                                          constraint.start_time % 100)
                    constraint_end = time(constraint.end_time // 100, 
                                        constraint.end_time % 100)
                    
                    # Check if time ranges overlap
                    if time_ranges_overlap(slot_start, slot_end, 
                                          constraint_start, constraint_end):
                        conflict = True
            
            elif isinstance(constraint, DateConstraint):
                # RD unavailable on specific date
                if slot_date and constraint.date == slot_date:
                    conflict = True
            
            elif isinstance(constraint, DateRangeConstraint):
                # RD unavailable during date range
                if slot_date and constraint.start_date <= slot_date <= constraint.end_date:
                    conflict = True
            
            if conflict:
                conflicting.append(token_text)
                break  # Don't add same token multiple times
    
    return conflicting


def time_ranges_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1


def display_conflict_report(report):
    """Display formatted conflict report."""
    click.echo("=" * 80)
    click.echo("REHEARSAL DIRECTOR CONFLICT REPORT")
    click.echo("=" * 80)
    
    if report['total_conflicts'] == 0:
        click.echo("\n✓ NO CONFLICTS FOUND")
        click.echo("All rehearsal directors are available during all scheduled venue times.")
        return
    
    click.echo(f"\n⚠ Found {report['total_conflicts']} potential scheduling conflicts")
    click.echo(f"Rehearsal Directors with conflicts: {', '.join(report['rds_with_conflicts'])}")
    click.echo("\n" + "=" * 80)
    
    # Group by RD
    conflicts_by_rd = {}
    for conflict in report['conflicts']:
        rhd_id = conflict['rhd_id']
        if rhd_id not in conflicts_by_rd:
            conflicts_by_rd[rhd_id] = []
        conflicts_by_rd[rhd_id].append(conflict)
    
    # Display by RD
    for rhd_id in sorted(conflicts_by_rd.keys()):
        click.echo(f"\n{'─' * 80}")
        click.echo(f"REHEARSAL DIRECTOR: {rhd_id}")
        click.echo(f"{'─' * 80}")
        
        for conflict in conflicts_by_rd[rhd_id]:
            click.echo(f"\n  Venue:      {conflict['venue']}")
            click.echo(f"  Date/Time:  {conflict['day']}, {conflict['date']} - {conflict['time_slot']}")
            click.echo(f"  Conflicts:  {', '.join(conflict['conflicting_constraints'])}")
            click.echo(f"\n  ⚠ RD {rhd_id} is unavailable during this time slot")
            click.echo(f"  Options:")
            click.echo(f"    • Assign substitute RD for this time slot")
            click.echo(f"    • Do not schedule {rhd_id}'s dances during this slot")
    
    click.echo("\n" + "=" * 80)
    click.echo("\nDIRECTOR ACTIONS:")
    click.echo("  1. Review each conflict above")
    click.echo("  2. Decide: assign substitute RD or avoid scheduling these dances")
    click.echo("  3. If assigning substitute, clear the conflict and notify substitute")
    click.echo("  4. Proceed with scheduling, avoiding conflicted time slots")
    click.echo("=" * 80)


def write_conflict_report_csv(report, output_path):
    """Write conflict report to CSV file."""
    import csv
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'rhd_id', 'venue', 'day', 'date', 'time_slot', 
                'conflicting_constraints'
            ])
            writer.writeheader()
            
            for conflict in report['conflicts']:
                writer.writerow({
                    'rhd_id': conflict['rhd_id'],
                    'venue': conflict['venue'],
                    'day': conflict['day'],
                    'date': conflict['date'],
                    'time_slot': conflict['time_slot'],
                    'conflicting_constraints': ', '.join(conflict['conflicting_constraints'])
                })
        
        click.echo(f"\n✓ Conflict report written to: {output_path}")
    except Exception as e:
        click.echo(f"❌ Error writing CSV: {e}", err=True)
# =============================================================================
if __name__ == '__main__':
    cli()