#!/usr/bin/env python3
"""
Populate the 'dancers' column in the Production workbook's production_program sheet.

Reads the dance_cast matrix from Look Up Tables workbook and generates a comma-separated,
alphabetically sorted list of dancers for each dance in the production program.

Usage:
    # Use workbook IDs from config/workbook_export.yaml
    python populate_production_dancers.py
    
    # Override with specific IDs
    python populate_production_dancers.py \\
        --lookup-workbook-id SPREADSHEET_ID \\
        --production-workbook-id SPREADSHEET_ID
"""

import os
import sys
import click
import yaml
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import Dict, List, Tuple


CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DEFAULT_CONFIG_PATH = 'config/workbook_export.yaml'


def load_workbook_ids_from_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, str]:
    """
    Load workbook IDs from YAML config file.
    
    Returns:
        Dict with 'lookup_tables' and 'production' keys mapped to spreadsheet IDs
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        workbooks = config.get('workbooks', {})
        
        return {
            'lookup_tables': workbooks.get('lookup_tables', ''),
            'production': workbooks.get('production', '')
        }
    except FileNotFoundError:
        click.echo(click.style(f"Config file not found: {config_path}", fg='yellow'))
        return {'lookup_tables': '', 'production': ''}
    except Exception as e:
        click.echo(click.style(f"Error reading config: {e}", fg='yellow'))
        return {'lookup_tables': '', 'production': ''}


def get_sheets_service():
    """Initialize Google Sheets service."""
    if not CREDENTIALS_PATH:
        click.echo(click.style("Error: GOOGLE_BUILDER_CREDENTIALS not set", fg='red'))
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def read_dance_cast_matrix(sheets_service, spreadsheet_id: str) -> Dict[str, List[str]]:
    """
    Read the dance_cast matrix and return a dict mapping dance_id -> list of dancer names.
    
    Matrix format:
    Row 1: dance_ids starting at column C
    Row 2: dance_names starting at column C  
    Column A (row 3+): dancer_ids
    Column B (row 3+): dancer_full_names
    Grid: 1 if dancer is in dance
    
    Returns:
        Dict mapping dance_id to sorted list of dancer full names
    """
    click.echo("Reading dance_cast matrix from Look Up Tables...")
    
    # Read the entire dance_cast sheet
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='dance_cast!A1:ZZ'  # Read everything
    ).execute()
    
    values = result.get('values', [])
    
    if len(values) < 3:
        click.echo(click.style("Error: dance_cast sheet is too small", fg='red'))
        sys.exit(1)
    
    # Parse header row (dance_ids start at column C = index 2)
    dance_ids = values[0][2:] if len(values[0]) > 2 else []
    click.echo(f"  Found {len(dance_ids)} dances")
    
    # Parse dancer rows (start at row 3 = index 2)
    dance_to_dancers = {dance_id: [] for dance_id in dance_ids}
    
    for row_idx in range(2, len(values)):
        row = values[row_idx]
        
        if len(row) < 2:
            continue  # Skip empty rows
        
        dancer_id = row[0]
        dancer_name = row[1]
        
        # Check which dances this dancer is in (starting at column C = index 2)
        for col_idx, dance_id in enumerate(dance_ids):
            grid_col = col_idx + 2  # Column C = index 2
            
            if grid_col < len(row):
                cell_value = str(row[grid_col]).strip()
                if cell_value == '1':
                    dance_to_dancers[dance_id].append(dancer_name)
    
    # Sort dancer lists alphabetically
    for dance_id in dance_to_dancers:
        dance_to_dancers[dance_id].sort()
    
    # Show summary
    total_dancers = sum(len(dancers) for dancers in dance_to_dancers.values())
    click.echo(f"  Loaded {total_dancers} total dancer assignments")
    
    return dance_to_dancers


def read_production_program(sheets_service, spreadsheet_id: str) -> List[List[str]]:
    """
    Read the production_program sheet.
    
    Returns:
        List of rows (including header)
    """
    click.echo("Reading production_program from Production workbook...")
    
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='production_program!A1:Z'
    ).execute()
    
    values = result.get('values', [])
    click.echo(f"  Found {len(values)-1} dances in production program")
    
    return values


def populate_dancers_column(
    sheets_service,
    spreadsheet_id: str,
    production_rows: List[List[str]],
    dance_to_dancers: Dict[str, List[str]]
) -> int:
    """
    Populate the 'dancers' column in production_program.
    
    Assumes columns are: line_no, dance_id, dance_name, choreographer, dancers
    
    Returns:
        Number of rows updated
    """
    click.echo("\nPopulating dancers column...")
    
    if len(production_rows) < 2:
        click.echo(click.style("  No data rows to update", fg='yellow'))
        return 0
    
    # Find the dancers column (should be column E = index 4)
    header = production_rows[0]
    
    try:
        dancers_col_idx = header.index('dancers')
    except ValueError:
        click.echo(click.style("  Error: 'dancers' column not found in header", fg='red'))
        sys.exit(1)
    
    try:
        dance_id_col_idx = header.index('dance_id')
    except ValueError:
        click.echo(click.style("  Error: 'dance_id' column not found in header", fg='red'))
        sys.exit(1)
    
    # Build update data
    updates = []
    updated_count = 0
    
    for row_idx in range(1, len(production_rows)):  # Skip header
        row = production_rows[row_idx]
        
        # Ensure row is long enough
        while len(row) <= dancers_col_idx:
            row.append('')
        
        # Get dance_id for this row
        if dance_id_col_idx >= len(row):
            continue
        
        dance_id = row[dance_id_col_idx]
        
        if not dance_id:
            continue
        
        # Get dancers for this dance
        dancers = dance_to_dancers.get(dance_id, [])
        
        if not dancers:
            click.echo(f"  ⚠️  No dancers found for {dance_id}")
            dancer_list = ""
        else:
            dancer_list = ", ".join(dancers)
            click.echo(f"  ✓ {dance_id}: {len(dancers)} dancers")
        
        # Update the row
        row[dancers_col_idx] = dancer_list
        updated_count += 1
    
    # Write back to sheet
    click.echo(f"\nWriting updates to production_program...")
    
    # Convert column index to letter
    dancers_col_letter = chr(ord('A') + dancers_col_idx)
    
    # Update just the dancers column (more efficient than entire sheet)
    range_name = f'production_program!{dancers_col_letter}2:{dancers_col_letter}'
    
    values_to_write = [[row[dancers_col_idx]] for row in production_rows[1:]]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body={'values': values_to_write}
    ).execute()
    
    return updated_count


@click.command()
@click.option('--lookup-workbook-id',
              help='Spreadsheet ID for Look Up Tables workbook (default: from config)')
@click.option('--production-workbook-id',
              help='Spreadsheet ID for Production workbook (default: from config)')
@click.option('--config', default=DEFAULT_CONFIG_PATH,
              help='Path to workbook config YAML file')
@click.option('--dry-run', is_flag=True,
              help='Show what would be updated without writing')
def main(lookup_workbook_id, production_workbook_id, config, dry_run):
    """
    Populate the dancers column in production_program.
    
    Reads dance_cast matrix from Look Up Tables workbook and generates
    alphabetically sorted, comma-separated dancer lists for each dance
    in the Production workbook's production_program sheet.
    
    If workbook IDs are not provided, reads them from config/workbook_export.yaml.
    """
    click.echo(click.style("\n=== Populate Production Dancers ===\n", fg='blue', bold=True))
    
    # Load from config if IDs not provided
    if not lookup_workbook_id or not production_workbook_id:
        click.echo(f"Loading workbook IDs from {config}...")
        config_ids = load_workbook_ids_from_config(config)
        
        lookup_workbook_id = lookup_workbook_id or config_ids.get('lookup_tables')
        production_workbook_id = production_workbook_id or config_ids.get('production')
        
        if not lookup_workbook_id or not production_workbook_id:
            click.echo(click.style(
                "Error: Workbook IDs not provided and not found in config.\n"
                "Either:\n"
                "  1. Use --lookup-workbook-id and --production-workbook-id options, or\n"
                f"  2. Set workbook IDs in {config}",
                fg='red'
            ))
            sys.exit(1)
        
        click.echo(click.style("  ✓ Loaded from config\n", fg='green'))
    
    # Initialize service
    sheets_service = get_sheets_service()
    
    # Step 1: Read dance_cast matrix
    dance_to_dancers = read_dance_cast_matrix(sheets_service, lookup_workbook_id)
    
    # Step 2: Read production_program
    production_rows = read_production_program(sheets_service, production_workbook_id)
    
    if dry_run:
        click.echo(click.style("\n--dry-run mode: No changes will be made\n", fg='yellow'))
        
        # Show what would be updated
        header = production_rows[0]
        dance_id_col = header.index('dance_id')
        
        for row in production_rows[1:]:
            if dance_id_col < len(row):
                dance_id = row[dance_id_col]
                dancers = dance_to_dancers.get(dance_id, [])
                dancer_list = ", ".join(dancers) if dancers else "(none)"
                click.echo(f"  {dance_id}: {dancer_list}")
        
        click.echo(click.style("\n✓ Dry run complete (no changes made)\n", fg='green'))
    else:
        # Step 3: Populate dancers column
        updated_count = populate_dancers_column(
            sheets_service,
            production_workbook_id,
            production_rows,
            dance_to_dancers
        )
        
        click.echo(click.style(f"\n✓ Updated {updated_count} dances in production_program\n", 
                              fg='green', bold=True))


if __name__ == '__main__':
    main()