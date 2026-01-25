#!/usr/bin/env python3
"""
Build Google Sheets workbooks from YAML specifications.
"""

import os
import sys
import click
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
import yaml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build as build_service
from googleapiclient.errors import HttpError
from rehearsal_scheduler.workbook_builder.formula_builder import build_formulas_for_sheet

# Load credentials
CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


@dataclass
class WorksheetSpec:
    """Specification for a single worksheet."""
    name: str
    columns: List[str]
    protected_rows: List[int] = field(default_factory=list)
    protected_columns: List[str] = field(default_factory=list)
    formulas: Dict[str, str] = field(default_factory=dict)
    auto_id_config: Dict[str, Any] = None
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'WorksheetSpec':
        """Load worksheet spec from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            columns=data['columns'],
            protected_rows=data.get('protected_rows', []),
            protected_columns=data.get('protected_columns', []),
            formulas=data.get('formulas', {}),
            auto_id_config=data.get('auto_id_config')
        )


def get_sheets_service():
    """Initialize Google Sheets service."""
    if not CREDENTIALS_PATH:
        click.echo(click.style("Error: GOOGLE_BUILDER_CREDENTIALS not set", fg='red'))
        click.echo("Set with: export GOOGLE_BUILDER_CREDENTIALS=/path/to/credentials.json")
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build_service('sheets', 'v4', credentials=creds)


def sheet_exists(sheets_service, spreadsheet_id: str, sheet_name: str) -> tuple[bool, int]:
    """
    Check if a sheet with the given name exists.
    
    Returns:
        Tuple of (exists, sheet_id). sheet_id is None if doesn't exist.
    """
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return True, sheet['properties']['sheetId']
        return False, None
    except HttpError:
        return False, None


def add_worksheet(sheets_service, spreadsheet_id: str, spec: WorksheetSpec, 
                 is_first: bool = False, force: bool = False):
    """Add or update a worksheet in the spreadsheet."""
    
    requests = []
    
    # Check if sheet exists
    exists, sheet_id = sheet_exists(sheets_service, spreadsheet_id, spec.name)
    
    if exists and not force and not is_first:
        click.echo(click.style(
            f"  ⚠️  Sheet '{spec.name}' already exists. Skipping (use --force to overwrite).", 
            fg='yellow'
        ))
        return
    
    # Get or create sheet
    if is_first:
        # Rename Sheet1
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': 0,
                        'title': spec.name
                    },
                    'fields': 'title'
                }
            }]}
        ).execute()
        sheet_id = 0
        click.echo(click.style(f"  ✓ Renamed Sheet1 to '{spec.name}'", fg='green'))
    
    elif exists and force:
        # Delete and recreate
        click.echo(click.style(f"  ✓ Deleting existing '{spec.name}'", fg='yellow'))
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{
                'deleteSheet': {'sheetId': sheet_id}
            }]}
        ).execute()
        
        # Create new
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{
                'addSheet': {
                    'properties': {'title': spec.name}
                }
            }]}
        ).execute()
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        click.echo(click.style(f"  ✓ Recreated worksheet: '{spec.name}'", fg='green'))
    
    else:
        # Create new sheet
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{
                'addSheet': {
                    'properties': {'title': spec.name}
                }
            }]}
        ).execute()
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        click.echo(click.style(f"  ✓ Created worksheet: '{spec.name}'", fg='green'))
    
    # Write headers
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{spec.name}!A1",
        valueInputOption='RAW',
        body={'values': [spec.columns]}
    ).execute()
    click.echo(f"    ✓ Headers: {', '.join(spec.columns)}")
    
    # Format header (bold + freeze)
    requests.append({
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': 0,
                'endRowIndex': 1
            },
            'cell': {
                'userEnteredFormat': {
                    'textFormat': {'bold': True}
                }
            },
            'fields': 'userEnteredFormat.textFormat.bold'
        }
    })
    
    requests.append({
        'updateSheetProperties': {
            'properties': {
                'sheetId': sheet_id,
                'gridProperties': {'frozenRowCount': 1}
            },
            'fields': 'gridProperties.frozenRowCount'
        }
    })
    
    # Auto-IDs
    if spec.auto_id_config:
        config = spec.auto_id_config
        col_index = spec.columns.index(config['column'])
        col_letter = chr(65 + col_index)
        
        ids = [[f"{config['prefix']}{i:02d}"] for i in range(1, config['count'] + 1)]
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{spec.name}!{col_letter}2:{col_letter}{config['count']+1}",
            valueInputOption='RAW',
            body={'values': ids}
        ).execute()
        click.echo(f"    ✓ Auto-IDs: {config['prefix']}01 to {config['prefix']}{config['count']:02d}")
    
    # Formulas
    if spec.formulas and spec.auto_id_config:
        row_count = spec.auto_id_config['count']
        formulas = build_formulas_for_sheet(spec.columns, spec.formulas, row_count)
        
        for col_name, (cell_ref, formula_str) in formulas.items():
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{spec.name}!{cell_ref}",
                valueInputOption='USER_ENTERED',
                body={'values': [[formula_str]]}
            ).execute()
            click.echo(f"    ✓ Formula: {col_name}")
    
    # Protected rows
    for row_num in spec.protected_rows:
        requests.append({
            'addProtectedRange': {
                'protectedRange': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_num - 1,  # 0-indexed
                        'endRowIndex': row_num
                    },
                    'description': f'Protected: Row {row_num}',
                    'warningOnly': False
                }
            }
        })
    
    if spec.protected_rows:
        click.echo(f"    ✓ Protected rows: {', '.join(map(str, spec.protected_rows))}")
    
    # Protected columns
    for col_name in spec.protected_columns:
        col_index = spec.columns.index(col_name)
        requests.append({
            'addProtectedRange': {
                'protectedRange': {
                    'range': {
                        'sheetId': sheet_id,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1,
                        'startRowIndex': 1  # Skip header
                    },
                    'description': f'Protected: {col_name}',
                    'warningOnly': False
                }
            }
        })
    
    if spec.protected_columns:
        click.echo(f"    ✓ Protected columns: {', '.join(spec.protected_columns)}")
    
    # Execute all batch requests
    if requests:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()


@click.group()
def cli():
    """Build Google Sheets workbooks from YAML specifications."""
    pass


@cli.command()
@click.option('--spec', type=click.Path(exists=True), required=True,
              help='Path to YAML spec file')
@click.option('--spreadsheet-id', required=True,
              help='Google Spreadsheet ID')
@click.option('--is-first', is_flag=True,
              help='Rename Sheet1 (for first sheet in new workbook)')
@click.option('--force', is_flag=True,
              help='Overwrite existing sheet')
def sheet(spec, spreadsheet_id, is_first, force):
    """Build a single sheet from YAML spec."""
    click.echo(click.style("="*60, fg='blue'))
    click.echo(click.style(f"Building sheet from: {spec}", fg='blue'))
    click.echo(click.style("="*60, fg='blue'))
    
    sheets_service = get_sheets_service()
    
    # Verify access
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        click.echo(click.style(f"✓ Accessed: {spreadsheet['properties']['title']}", fg='green'))
    except HttpError as e:
        click.echo(click.style(f"✗ Cannot access: {e}", fg='red'))
        click.echo("\nMake sure:")
        click.echo("1. The spreadsheet exists")
        click.echo("2. It's shared with the service account as Editor")
        sys.exit(1)
    
    # Load and build
    worksheet_spec = WorksheetSpec.from_yaml(spec)
    add_worksheet(sheets_service, spreadsheet_id, worksheet_spec, is_first, force)
    
    click.echo(click.style("\n✓ Sheet complete!", fg='green'))
    click.echo(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")


@cli.command()
@click.option('--workbook', required=True,
              help='Workbook name (e.g., lookup_tables)')
@click.option('--spreadsheet-id', required=True,
              help='Google Spreadsheet ID')
@click.option('--force', is_flag=True,
              help='Overwrite existing sheets')
def workbook(workbook, spreadsheet_id, force):
    """Build all sheets in a workbook from spec directory."""
    click.echo(click.style("="*60, fg='blue'))
    click.echo(click.style(f"Building workbook: {workbook}", fg='blue'))
    click.echo(click.style("="*60, fg='blue'))
    
    # Find spec files
    config_dir = Path(__file__).parent.parent.parent / 'config' / 'workbook_specs' / workbook
    
    if not config_dir.exists():
        click.echo(click.style(f"✗ Directory not found: {config_dir}", fg='red'))
        sys.exit(1)
    
    spec_files = sorted(config_dir.glob('*.yaml'))
    
    if not spec_files:
        click.echo(click.style(f"✗ No YAML files found in: {config_dir}", fg='red'))
        sys.exit(1)
    
    click.echo(f"Found {len(spec_files)} sheet spec(s):")
    for f in spec_files:
        click.echo(f"  - {f.name}")
    
    # Verify access
    sheets_service = get_sheets_service()
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        click.echo(click.style(f"\n✓ Accessed: {spreadsheet['properties']['title']}", fg='green'))
    except HttpError as e:
        click.echo(click.style(f"✗ Cannot access: {e}", fg='red'))
        sys.exit(1)
    
    # Build sheets
    for i, spec_file in enumerate(spec_files):
        click.echo(f"\n--- Sheet {i+1}/{len(spec_files)} ---")
        worksheet_spec = WorksheetSpec.from_yaml(spec_file)
        add_worksheet(sheets_service, spreadsheet_id, worksheet_spec, is_first=(i == 0), force=force)
    
    click.echo(click.style("\n" + "="*60, fg='blue'))
    click.echo(click.style("✓ Workbook complete!", fg='green'))
    click.echo(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    click.echo(click.style("="*60 + "\n", fg='blue'))


if __name__ == '__main__':
    cli()
