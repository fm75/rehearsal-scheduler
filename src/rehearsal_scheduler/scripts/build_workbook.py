#!/usr/bin/env python3
"""
Build Google Sheets workbooks from YAML specifications.

Usage:
    # Build single sheet
    python build_workbook.py --spec config/workbook_specs/lookup_tables/dances.yaml --spreadsheet-id SHEET_ID
    
    # Build all sheets in a workbook
    python build_workbook.py --workbook lookup_tables --spreadsheet-id SHEET_ID
    
    # Interactive mode
    python build_workbook.py
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import yaml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Load credentials
CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def column_letter(col_name, columns):
    if col_name not in columns:
        return None
    col_index = columns.index(col_name)
    if col_index > 25:
        raise ValueError(f"found {col_name}, but it is not in columns (A-Z)")
    return chr(65 + col_index)
    

def top_cell(col_name, columns, begin=2):
    letter = column_letter(col_name, columns)
    if letter is not None:
        return f"{letter}{begin}"
    print(f"{col_name} in formulas was not found in columns {columns}.")
    print(f"Skipping implementation of its formula")
    return None

    
def target_column_condition(col_name, columns, end, begin=2):
    start_cell = top_cell(col_name, columns, begin)
    col_letter = column_letter(col_name, columns)
    if start_cell:
        return f'=ARRAYFORMULA((IF(ISBLANK({start_cell}:{col_letter}{end}),"",'


def formula_component(rule, columns, end, begin=2):
    for col_name in columns:
        col_index = columns.index(col_name)
        col_letter = chr(65 + col_index)
        if col_name in rule:
            rule = rule.replace(col_name, f"{col_letter}{begin}:{col_letter}{end}")
    rule += ")))"
    return rule


def array_formula(target, value):
    return [[target + value]]


def update_args(spec, end):
    for col_name, formula in spec.formulas.items():
        tc = top_cell(col_name, spec.columns)
        af = array_formula(target_column_condition(col_name, spec.columns, end),
                           formula_component(formula, spec.columns, end))
        return tc, af

@dataclass
class WorksheetSpec:
    """Specification for a single worksheet."""
    name: str
    columns: List[str]
    protected_columns: List[str] = None
    formulas: Dict[str, str] = None
    auto_id_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.protected_columns is None:
            self.protected_columns = []
        if self.formulas is None:
            self.formulas = {}
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'WorksheetSpec':
        """Load worksheet spec from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            columns=data['columns'],
            protected_columns=data.get('protected_columns', []),
            formulas=data.get('formulas', {}),
            auto_id_config=data.get('auto_id_config')
        )


def get_sheets_service():
    """Initialize Google Sheets service."""
    if not CREDENTIALS_PATH:
        print("Error: GOOGLE_BUILDER_CREDENTIALS environment variable not set")
        print("Set it with: export GOOGLE_BUILDER_CREDENTIALS=/path/to/credentials.json")
        sys.exit(1)
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def add_worksheet(sheets_service, spreadsheet_id: str, spec: WorksheetSpec, is_first: bool = False):
    """Add or update a worksheet in the spreadsheet."""
    
    requests = []
    
    # Get or create sheet
    if is_first:
        # Rename Sheet1 - execute immediately
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
        print(f"  ✓ Renamed Sheet1 to '{spec.name}'")
    else:
        # Check if exists
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_sheet = None
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == spec.name:
                existing_sheet = sheet
                break
        
        if existing_sheet:
            sheet_id = existing_sheet['properties']['sheetId']
            print(f"  ✓ Worksheet exists: '{spec.name}' (updating)")
        else:
            requests.append({
                'addSheet': {
                    'properties': {'title': spec.name}
                }
            })
            response = sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            requests = []
            print(f"  ✓ Created worksheet: '{spec.name}'")
    
    # Write headers
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{spec.name}!A1",
        valueInputOption='RAW',
        body={'values': [spec.columns]}
    ).execute()
    print(f"    ✓ Headers: {', '.join(spec.columns)}")
    
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
        print(f"    ✓ Auto-IDs: {config['prefix']}01 to {config['prefix']}{config['count']:02d}")
    
    # Formulas
    for col_name, formula in spec.formulas.items():
        # col_index = spec.columns.index(col_name)
        # col_letter = chr(65 + col_index)
        
        # base = formula.lstrip('=')
        # array_formula = f"=ArrayFormula(IF(ROW(A:A)=1,\"\",{base}))"
        beg = 2
        end = spec.auto_id_config['count'] + 1
        tc, formula = update_args(spec, end)

        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{spec.name}!{tc}",
            # range=f"{spec.name}!{col_letter}2",
            valueInputOption='USER_ENTERED',
            body={'values': formula}
            # body={'values': [[array_formula]]}
        ).execute()
        print(f"    ✓ Formula: {col_name}")
    
    # Protections
    requests.append({
        'addProtectedRange': {
            'protectedRange': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'description': 'Protected: Headers',
                'warningOnly': False
            }
        }
    })
    
    for col_name in spec.protected_columns:
        col_index = spec.columns.index(col_name)
        requests.append({
            'addProtectedRange': {
                'protectedRange': {
                    'range': {
                        'sheetId': sheet_id,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1,
                        'startRowIndex': 1
                    },
                    'description': f'Protected: {col_name}',
                    'warningOnly': False
                }
            }
        })
    
    if spec.protected_columns:
        print(f"    ✓ Protected: header + {', '.join(spec.protected_columns)}")
    
    # Execute
    if requests:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()


def build_sheet(spreadsheet_id: str, spec_file: str, is_first: bool = False):
    """Build a single sheet from spec file."""
    print(f"\n{'='*60}")
    print(f"Building sheet from: {spec_file}")
    print(f"{'='*60}")
    
    sheets_service = get_sheets_service()
    
    # Verify access
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print(f"✓ Accessed workbook: {spreadsheet['properties']['title']}")
    except HttpError as e:
        print(f"✗ Cannot access: {e}")
        print("\nMake sure:")
        print("1. The spreadsheet exists")
        print("2. It's shared with the service account as Editor")
        sys.exit(1)
    
    # Load spec and build
    spec = WorksheetSpec.from_yaml(spec_file)
    add_worksheet(sheets_service, spreadsheet_id, spec, is_first=is_first)
    
    print(f"\n✓ Sheet complete!")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"{'='*60}\n")


def build_workbook(spreadsheet_id: str, workbook_name: str):
    """Build all sheets in a workbook from spec directory."""
    print(f"\n{'='*60}")
    print(f"Building workbook: {workbook_name}")
    print(f"{'='*60}")
    
    # Find all YAML files in workbook directory
    config_dir = Path(__file__).parent.parent.parent / 'config' / 'workbook_specs' / workbook_name
    
    if not config_dir.exists():
        print(f"✗ Directory not found: {config_dir}")
        sys.exit(1)
    
    spec_files = sorted(config_dir.glob('*.yaml'))
    
    if not spec_files:
        print(f"✗ No YAML files found in: {config_dir}")
        sys.exit(1)
    
    print(f"Found {len(spec_files)} sheet specs:")
    for f in spec_files:
        print(f"  - {f.name}")
    
    # Build each sheet
    sheets_service = get_sheets_service()
    
    # Verify access
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print(f"\n✓ Accessed: {spreadsheet['properties']['title']}")
    except HttpError as e:
        print(f"✗ Cannot access: {e}")
        sys.exit(1)
    
    # Build sheets
    for i, spec_file in enumerate(spec_files):
        print(f"\n--- Sheet {i+1}/{len(spec_files)} ---")
        spec = WorksheetSpec.from_yaml(spec_file)
        add_worksheet(sheets_service, spreadsheet_id, spec, is_first=(i == 0))
    
    print(f"\n{'='*60}")
    print(f"✓ Workbook complete!")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build Google Sheets workbooks from YAML specifications'
    )
    parser.add_argument(
        '--spec',
        help='Path to single sheet YAML spec file'
    )
    parser.add_argument(
        '--workbook',
        help='Workbook name (looks in config/workbook_specs/<name>/)'
    )
    parser.add_argument(
        '--spreadsheet-id',
        help='Google Spreadsheet ID'
    )
    parser.add_argument(
        '--is-first',
        action='store_true',
        help='Rename Sheet1 (use for first sheet in new workbook)'
    )
    
    args = parser.parse_args()
    
    # Interactive mode if no args
    if not args.spec and not args.workbook:
        print("Google Sheets Workbook Builder")
        print("=" * 60)
        
        mode = input("\nBuild (s)ingle sheet or (w)hole workbook? [s/w]: ").strip().lower()
        
        if mode == 'w':
            workbook = input("Workbook name (lookup_tables/scheduling/production): ").strip()
            spreadsheet_id = input("Spreadsheet ID: ").strip()
            build_workbook(spreadsheet_id, workbook)
        else:
            spec_file = input("Path to YAML spec: ").strip()
            spreadsheet_id = input("Spreadsheet ID: ").strip()
            is_first = input("Is this the first sheet? [y/n]: ").strip().lower() == 'y'
            build_sheet(spreadsheet_id, spec_file, is_first)
    
    # Command-line mode
    elif args.workbook:
        if not args.spreadsheet_id:
            print("Error: --spreadsheet-id required with --workbook")
            sys.exit(1)
        build_workbook(args.spreadsheet_id, args.workbook)
    
    elif args.spec:
        if not args.spreadsheet_id:
            print("Error: --spreadsheet-id required with --spec")
            sys.exit(1)
        build_sheet(args.spreadsheet_id, args.spec, args.is_first)


if __name__ == '__main__':
    main()
