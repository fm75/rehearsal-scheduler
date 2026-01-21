"""
Base interfaces for data persistence.

This module defines abstract interfaces that allow the application to work
with different data sources (CSV, Google Sheets, databases) without changing
business logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path


class DataSource(ABC):             # pragma: no cover
    """Abstract base class for data sources."""
    
    @abstractmethod
    def read_records(self) -> List[Dict[str, Any]]:
        """
        Read all records from the data source.
        
        Returns:
            List of dictionaries, where each dict represents a row with
            column names as keys.
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get a human-readable name for this data source."""
        pass


class CSVDataSource(DataSource):
    """Data source for CSV files."""
    
    def __init__(self, filepath: Path):
        """
        Initialize CSV data source.
        
        Args:
            filepath: Path to the CSV file
        """
        self.filepath = Path(filepath)
    
    def read_records(self) -> List[Dict[str, Any]]:
        """Read records from CSV file."""
        import csv
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def get_source_name(self) -> str:
        """Return the filename."""
        return self.filepath.name


class GoogleSheetsDataSource(DataSource):
    """Data source for Google Sheets."""
    
    def __init__(
        self, 
        sheet_id_or_url: str, 
        credentials_path: Path,
        worksheet: str = '0'
    ):
        """
        Initialize Google Sheets data source.
        
        Args:
            sheet_id_or_url: Sheet ID or full URL
            credentials_path: Path to service account JSON file
            worksheet: Worksheet index (0-based) or name
        """
        self.sheet_id_or_url = sheet_id_or_url
        self.credentials_path = Path(credentials_path)
        self.worksheet = worksheet
        self._sheet_title = None
        self._worksheet_title = None
    
    def read_records(self) -> List[Dict[str, Any]]:
        """Read records from Google Sheet."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ImportError(
                "gspread and google-auth packages required for Google Sheets. "
                "Install with: pip install gspread google-auth"
            )
        
        # Authenticate
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        creds = Credentials.from_service_account_file(
            str(self.credentials_path), 
            scopes=scopes
        )
        client = gspread.authorize(creds)
        
        # Open sheet
        if self.sheet_id_or_url.startswith('http'):
            sheet = client.open_by_url(self.sheet_id_or_url)
        else:
            sheet = client.open_by_key(self.sheet_id_or_url)
        
        self._sheet_title = sheet.title
        
        # Get worksheet
        if self.worksheet.isdigit():
            ws = sheet.get_worksheet(int(self.worksheet))
        else:
            ws = sheet.worksheet(self.worksheet)
        
        self._worksheet_title = ws.title
        
        return ws.get_all_records()
    
    def get_source_name(self) -> str:
        """Return sheet and worksheet titles."""
        if self._sheet_title and self._worksheet_title:
            return f"{self._sheet_title} / {self._worksheet_title}"
        return self.sheet_id_or_url


class DataSourceFactory:
    """Factory for creating appropriate data sources."""
    
    @staticmethod
    def create_csv(filepath: str) -> CSVDataSource:
        """Create a CSV data source."""
        return CSVDataSource(Path(filepath))
    
    @staticmethod
    def create_sheets(
        sheet_id_or_url: str,
        credentials_path: str,
        worksheet: str = '0'
    ) -> GoogleSheetsDataSource:
        """Create a Google Sheets data source."""
        return GoogleSheetsDataSource(
            sheet_id_or_url,
            Path(credentials_path),
            worksheet
        )