#!/usr/bin/env python3
"""
Build Google Sheets workbooks from specifications.

This version works with EXISTING workbooks that are manually created and shared.
It adds worksheets, protected ranges, formulas, and auto-generated IDs.
"""

import os
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Load credentials
CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
if not CREDENTIALS_PATH:
    print("Error: GOOGLE_BUILDER_CREDENTIALS environment variable not set")
    sys.exit(1)

print(f"Using credentials: {CREDENTIALS_PATH}")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


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


@dataclass  
class WorkbookSpec:
    """Specification for a complete workbook."""
    name: str
    worksheets: List[WorksheetSpec]


def get_sheets_service():
    """Initialize Google Sheets service."""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def add_worksheet(sheets_service, spreadsheet_id: str, spec: WorksheetSpec, is_first: bool = False):
    """Add or update a worksheet."""
    
    requests = []
    
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
            print(f"  ✓ Worksheet exists: '{spec.name}'")
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
        col_index = spec.columns.index(col_name)
        col_letter = chr(65 + col_index)
        
        base = formula.lstrip('=')
        array_formula = f"=ArrayFormula(IF(ROW(A:A)=1,\"\",{base}))"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{spec.name}!{col_letter}2",
            valueInputOption='USER_ENTERED',
            body={'values': [[array_formula]]}
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


def build_workbook(spreadsheet_id: str, spec: WorkbookSpec):
    """Build worksheets in existing workbook."""
    print(f"\n{'='*60}")
    print(f"Building: {spec.name}")
    print(f"ID: {spreadsheet_id}")
    print(f"{'='*60}")
    
    sheets_service = get_sheets_service()
    
    # Verify access
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print(f"✓ Accessed: {spreadsheet['properties']['title']}")
    except HttpError as e:
        print(f"✗ Cannot access: {e}")
        print("\nMake sure the spreadsheet is shared with the service account as Editor")
        sys.exit(1)
    
    # Build worksheets
    for i, ws_spec in enumerate(spec.worksheets):
        add_worksheet(sheets_service, spreadsheet_id, ws_spec, is_first=(i == 0))
    
    print(f"\n✓ Complete!")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Spec
    lookup_tables_spec = WorkbookSpec(
        name='Look Up Tables',
        worksheets=[
            WorksheetSpec(
                name='dances',
                columns=['dance_id', 'name', 'music', 'duration', 'minutes', 'seconds', 'duration_seconds'],
                protected_columns=['dance_id', 'duration', 'duration_seconds'],
                formulas={
                    'duration': '=TO_TEXT(E2)&":"&TO_TEXT(F2)',
                    'duration_seconds': '=60*E2+F2'
                },
                auto_id_config={
                    'column': 'dance_id',
                    'prefix': 'd_',
                    'count': 50
                }
            )
        ]
    )
    
    # Get spreadsheet ID
    spreadsheet_id = input("Enter Google Spreadsheet ID: ").strip()
    
    if not spreadsheet_id:
        print("Error: Spreadsheet ID required")
        sys.exit(1)
    
    # Build it
    build_workbook(spreadsheet_id, lookup_tables_spec)