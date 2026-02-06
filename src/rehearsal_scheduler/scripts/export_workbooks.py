#!/usr/bin/env python3
"""
Export Google Sheets workbooks to CSV files.

Exports all sheets from specified workbooks to organized CSV directory structure.
"""

import os
import sys
import csv
import click
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_sheets_service():
    """Initialize Google Sheets service."""
    if not CREDENTIALS_PATH:
        click.echo(click.style("Error: GOOGLE_BUILDER_CREDENTIALS not set", fg='red'))
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def export_sheet_to_csv(sheets_service, spreadsheet_id: str, sheet_name: str, 
                        output_path: Path):
    """
    Export a single sheet to CSV.
    
    Args:
        sheets_service: Google Sheets API service
        spreadsheet_id: Spreadsheet ID
        sheet_name: Name of sheet to export
        output_path: Path to output CSV file
    """
    # Read all data from sheet
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:ZZ"  # Read up to column ZZ
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        click.echo(click.style(f"    ⚠️  Sheet '{sheet_name}' is empty", fg='yellow'))
        return
    
    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Normalize row lengths (pad short rows with empty strings)
        max_cols = max(len(row) for row in values)
        for row in values:
            padded_row = row + [''] * (max_cols - len(row))
            writer.writerow(padded_row)
    
    click.echo(click.style(f"    ✓ {sheet_name}.csv ({len(values)} rows)", fg='green'))


def export_workbook(sheets_service, spreadsheet_id: str, output_dir: Path):
    """
    Export all sheets from a workbook to CSV files.
    
    Args:
        sheets_service: Google Sheets API service
        spreadsheet_id: Spreadsheet ID
        output_dir: Directory to write CSV files
        
    Returns:
        Number of sheets exported
    """
    # Get workbook metadata
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    title = spreadsheet['properties']['title']
    sheets = spreadsheet.get('sheets', [])
    
    click.echo(f"\n  Workbook: {title}")
    click.echo(f"  Sheets: {len(sheets)}")
    
    # Export each sheet
    for sheet in sheets:
        sheet_name = sheet['properties']['title']
        output_path = output_dir / f"{sheet_name}.csv"
        
        try:
            export_sheet_to_csv(sheets_service, spreadsheet_id, sheet_name, output_path)
        except Exception as e:
            click.echo(click.style(f"    ✗ Error exporting '{sheet_name}': {e}", fg='red'))
    
    return len(sheets)


@click.group()
def cli():
    """Export Google Sheets workbooks to CSV files."""
    pass


@cli.command()
@click.option('--spreadsheet-id', required=True,
              help='Google Spreadsheet ID')
@click.option('--output-dir', type=click.Path(), required=True,
              help='Output directory for CSV files')
def workbook(spreadsheet_id, output_dir):
    """Export all sheets from a single workbook to CSV."""
    output_path = Path(output_dir)
    
    click.echo(click.style("="*60, fg='blue'))
    click.echo(click.style("Exporting workbook to CSV", fg='blue'))
    click.echo(click.style("="*60, fg='blue'))
    
    sheets_service = get_sheets_service()
    
    try:
        count = export_workbook(sheets_service, spreadsheet_id, output_path)
        click.echo(click.style(f"\n✓ Exported {count} sheets to {output_path}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--config', type=click.Path(exists=True),    
              default="config/workbook_config.yaml",
              help='YAML config file with workbook IDs')
@click.option('--output-dir', type=click.Path(), required=True,
              help='Base output directory (creates subdirs per workbook)')
def all_workbooks(config, output_dir):
    """Export all configured workbooks to organized directory structure."""
    import yaml
    
    # Load config
    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)
    
    workbooks = config_data.get('workbooks', {})
    
    if not workbooks:
        click.echo(click.style("No workbooks found in config", fg='red'))
        sys.exit(1)
    
    click.echo(click.style("="*60, fg='blue'))
    click.echo(click.style(f"Exporting {len(workbooks)} workbooks to CSV", fg='blue'))
    click.echo(click.style("="*60, fg='blue'))
    
    sheets_service = get_sheets_service()
    base_path = Path(output_dir)
    
    total_sheets = 0
    
    for workbook_name, spreadsheet_id in workbooks.items():
        click.echo(click.style(f"\n📁 {workbook_name}", fg='cyan', bold=True))
        
        output_path = base_path / workbook_name
        
        try:
            count = export_workbook(sheets_service, spreadsheet_id, output_path)
            total_sheets += count
        except Exception as e:
            click.echo(click.style(f"  ✗ Error: {e}", fg='red'))
            continue
    
    click.echo(click.style("\n" + "="*60, fg='blue'))
    click.echo(click.style(f"✓ Exported {total_sheets} total sheets", fg='green'))
    click.echo(click.style(f"  Location: {base_path}", fg='green'))
    click.echo(click.style("="*60, fg='blue'))


if __name__ == '__main__':
    cli()
