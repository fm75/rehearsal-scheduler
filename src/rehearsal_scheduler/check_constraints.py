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
@click.option('--worksheet', '-w', default=0,
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
            if worksheet.isdigit():
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


if __name__ == '__main__':
    cli()