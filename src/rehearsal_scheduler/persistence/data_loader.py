# Add this method to SchedulingDataLoader class in data_loader.py
#!/usr/bin/env python3
"""
Data loader for rehearsal scheduling - reads from Google Sheets into pandas DataFrames.

Provides a unified interface for loading scheduling data regardless of source.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import yaml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


CREDENTIALS_PATH = os.getenv('GOOGLE_BUILDER_CREDENTIALS') or os.getenv('GOOGLE_TEST_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


class SchedulingDataLoader:
    """
    Load scheduling data from Google Sheets into pandas DataFrames.
    
    Provides consistent DataFrame structure regardless of source.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize loader with configuration.
        
        Args:
            config_path: Path to YAML config with workbook IDs and sheet names
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.workbooks = self.config.get('workbooks', {})
        self.sheets = self.config.get('sheets', {})
        
        # Initialize Google Sheets service
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=creds)
    
    def _read_sheet_to_df(self, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
        """
        Read a Google Sheet into a DataFrame.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of sheet to read
            
        Returns:
            DataFrame with data from sheet
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:ZZ"
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            return pd.DataFrame()
        
        # First row is header
        header = values[0]
        data = values[1:]
        
        # Pad rows to match header length
        max_cols = len(header)
        padded_data = [row + [''] * (max_cols - len(row)) for row in data]
        
        return pd.DataFrame(padded_data, columns=header)
    
    def load_rehearsals(self) -> pd.DataFrame:
        """
        Load rehearsal schedule.
        
        Returns:
            DataFrame with columns: rehearsal_id, venue_id, venue_name, date, weekday, start_time, end_time
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling']['rehearsals']
        
        return self._read_sheet_to_df(scheduling_id, sheet_name)
    
    def load_rd_constraints(self) -> pd.DataFrame:
        """
        Load RD constraints.
        
        Returns:
            DataFrame with columns: rd_id, full_name, constraints, (optional: ai_translation, raw_constraints_from_form)
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling']['rd_constraints']
        
        return self._read_sheet_to_df(scheduling_id, sheet_name)
    
    def load_dancer_constraints(self) -> pd.DataFrame:
        """
        Load dancer constraints.
        
        Returns:
            DataFrame with columns: dancer_id, full_name, constraints, (optional: ai_translation, raw_constraints_from_form)
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling']['dancer_constraints']
        
        return self._read_sheet_to_df(scheduling_id, sheet_name)
    
    def load_dance_groups(self) -> pd.DataFrame:
        """
        Load dance group assignments.
        
        Returns:
            DataFrame with columns: dance_id, group_id
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling'].get('dance_groups', 'dance_groups')
        
        return self._read_sheet_to_df(scheduling_id, sheet_name)


    def load_dance_cast(self) -> pd.DataFrame:
        """
        Load dance casting matrix.
        
        Returns:
            DataFrame with dance_ids as columns, dancer_ids as index
        """
        lookup_id = self.workbooks['lookup_tables']
        sheet_name = self.sheets['lookup_tables'].get('dance_cast', 'dance_cast')
        
        df = self._read_sheet_to_df(lookup_id, sheet_name)
        
        # Sheet structure:
        # Row 1 (header): dancer_id, full_name, d_01, d_02, d_03, ...
        # Row 2: blank, blank, dance_name, dance_name, ... (skip this)
        # Row 3+: dancer_id, dancer_name, 1/0, 1/0, ...
        
        if df.empty or len(df) < 2:
            return pd.DataFrame()
        
        # Dance IDs are already in the column headers! (columns 2+)
        dance_ids = df.columns[2:]  # Skip 'dancer_id' and 'full_name'
        
        # Skip row 0 (dance names row), start from row 1 (first dancer)
        data_rows = df.iloc[1:].copy()
        
        # Set dancer_id as index
        data_rows.index = data_rows['dancer_id']
        data_rows.index.name = 'dancer_id'
        
        # Keep only the dance columns (drop dancer_id and full_name)
        grid = data_rows[dance_ids]
        
        return grid    


    def load_dances(self) -> pd.DataFrame:
        """
        Load dance information.
        
        Returns:
            DataFrame with dance details
        """
        lookup_id = self.workbooks['lookup_tables']
        sheet_name = self.sheets['lookup_tables'].get('dances', 'dances')
        
        return self._read_sheet_to_df(lookup_id, sheet_name)
    

    def load_dancers(self) -> pd.DataFrame:
        """
        Load dancer information.
        
        Returns:
            DataFrame with dancer details
        """
        lookup_id = self.workbooks['lookup_tables']
        sheet_name = self.sheets['lookup_tables'].get('dancers', 'dancers')
        
        return self._read_sheet_to_df(lookup_id, sheet_name)
    

    def load_group_cast(self) -> pd.DataFrame:
        """
        Load group casting matrix (Scheduling workbook version).
        
        Returns:
            DataFrame in matrix format with dancer_ids as index, dg_ids as columns
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling'].get('group_cast', 'group_cast')
        
        df = self._read_sheet_to_df(scheduling_id, sheet_name)
        
        # Same matrix format as dance_cast:
        # Row 0: dg_ids (d_01_g_01, d_02, etc.) starting at column C (index 2)
        # Row 1+: dancer data (dancer_id, dancer_name, then 1/0 grid)
        
        if df.empty or len(df) < 2:
            return pd.DataFrame()
        
        # Dance group IDs are in column headers (row 1 of sheet became headers)
        dg_ids = df.columns[2:]  # Skip 'dancer_id' and 'full_name'
        
        # Skip row 0 (which has group names for reference), start from row 1
        data_rows = df.iloc[1:].copy()
        
        # Set dancer_id as index
        data_rows.index = data_rows['dancer_id']
        data_rows.index.name = 'dancer_id'
        
        # Keep only the group columns (drop dancer_id and full_name)
        grid = data_rows[dg_ids]
        
        return grid


    def load_allotted(self) -> pd.DataFrame:
        """
        Load time allotments (RD requests for rehearsal time per dance group).
        
        Returns:
            DataFrame with columns: rd_id, rd_name, minutes, dg_id, dg_name
        """
        scheduling_id = self.workbooks['scheduling']
        sheet_name = self.sheets['scheduling'].get('allotted', 'allotted')
        
        df = self._read_sheet_to_df(scheduling_id, sheet_name)
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert minutes to numeric, handling any formatting issues
        if 'minutes' in df.columns:
            df['minutes'] = pd.to_numeric(df['minutes'], errors='coerce')
        
        return df

    

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        Load all scheduling data.
        
        Returns:
            Dictionary mapping data type to DataFrame
        """
        return {
            'rehearsals': self.load_rehearsals(),
            'rd_constraints': self.load_rd_constraints(),
            'dancer_constraints': self.load_dancer_constraints(),
            'dance_groups': self.load_dance_groups(),
            'dance_cast': self.load_dance_cast(),  # For production programs
            'group_cast': self.load_group_cast(),  # For scheduling
            'dances': self.load_dances(),
            'dancers': self.load_dancers(),
            'allotted': self.load_allotted(),
        }


def load_from_csv(data_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Load scheduling data from CSV files.
    
    Provides same DataFrame structure as SchedulingDataLoader for consistency.
    
    Args:
        data_dir: Directory containing CSV files
        
    Returns:
        Dictionary mapping data type to DataFrame
    """
    data_path = Path(data_dir)
    
    return {
        'rehearsals': pd.read_csv(data_path / 'rehearsals.csv'),
        'rd_constraints': pd.read_csv(data_path / 'rd_constraints.csv'),
        'dancer_constraints': pd.read_csv(data_path / 'dancer_constraints.csv'),
        'dance_groups': pd.read_csv(data_path / 'dance_groups.csv'),
        'dance_cast': pd.read_csv(data_path / 'dance_cast.csv', index_col=0),  # dancer_id as index
        'dances': pd.read_csv(data_path / 'dances.csv'),
        'dancers': pd.read_csv(data_path / 'dancers.csv'),
        'rds': pd.read_csv(data_path / 'rds.csv'),
    }


if __name__ == '__main__':
    # Quick test
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_loader.py config.yaml")
        sys.exit(1)
    
    loader = SchedulingDataLoader(sys.argv[1])
    data = loader.load_all()
    
    print("Loaded data:")
    for name, df in data.items():
        print(f"  {name}: {len(df)} rows × {len(df.columns)} columns")


