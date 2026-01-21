"""
Tests for persistence base module.
"""

import pytest
from pathlib import Path
import csv

from rehearsal_scheduler.persistence.base import (
    CSVDataSource,
    GoogleSheetsDataSource,
    DataSourceFactory
)


class TestCSVDataSource:
    """Tests for CSVDataSource."""
    
    def test_read_records_from_csv(self, tmp_path):
        """Test reading records from a CSV file."""
        # Create a temporary CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name', 'value'])
            writer.writeheader()
            writer.writerow({'id': '1', 'name': 'Alice', 'value': '100'})
            writer.writerow({'id': '2', 'name': 'Bob', 'value': '200'})
        
        # Read with CSVDataSource
        source = CSVDataSource(csv_file)
        records = source.read_records()
        
        assert len(records) == 2
        assert records[0]['id'] == '1'
        assert records[0]['name'] == 'Alice'
        assert records[0]['value'] == '100'
        assert records[1]['id'] == '2'
        assert records[1]['name'] == 'Bob'
    
    def test_get_source_name(self, tmp_path):
        """Test getting source name returns filename."""
        csv_file = tmp_path / "my_data.csv"
        csv_file.touch()
        
        source = CSVDataSource(csv_file)
        assert source.get_source_name() == "my_data.csv"
    
    def test_read_empty_csv(self, tmp_path):
        """Test reading empty CSV file."""
        csv_file = tmp_path / "empty.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name'])
            writer.writeheader()
        
        source = CSVDataSource(csv_file)
        records = source.read_records()
        
        assert len(records) == 0
    
    def test_read_nonexistent_file_raises_error(self):
        """Test that reading nonexistent file raises FileNotFoundError."""
        source = CSVDataSource(Path("/nonexistent/file.csv"))
        
        with pytest.raises(FileNotFoundError):
            source.read_records()
    
    def test_accepts_string_path(self, tmp_path):
        """Test CSVDataSource accepts string path."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id'])
            writer.writeheader()
            writer.writerow({'id': '1'})
        
        # Pass as string, not Path
        source = CSVDataSource(str(csv_file))
        records = source.read_records()
        
        assert len(records) == 1


class TestGoogleSheetsDataSource:
    """Tests for GoogleSheetsDataSource."""
    
    def test_initialization(self, tmp_path):
        """Test GoogleSheetsDataSource initialization."""
        creds_file = tmp_path / "creds.json"
        creds_file.touch()
        
        source = GoogleSheetsDataSource(
            "sheet_id_123",
            creds_file,
            "0"
        )
        
        assert source.sheet_id_or_url == "sheet_id_123"
        assert source.worksheet == "0"
    
    def test_get_source_name_before_read(self, tmp_path):
        """Test source name before reading returns sheet ID."""
        creds_file = tmp_path / "creds.json"
        creds_file.touch()
        
        source = GoogleSheetsDataSource("sheet_123", creds_file, "0")
        assert source.get_source_name() == "sheet_123"
    
    def test_read_records_from_sheet(self, tmp_path, monkeypatch):
        """Test reading records from Google Sheet."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create mock classes
        class MockWorksheet:
            title = 'Sheet1'
            
            def get_all_records(self):
                return [
                    {'id': '1', 'name': 'Alice'},
                    {'id': '2', 'name': 'Bob'}
                ]
        
        class MockSheet:
            title = 'Test Sheet'
            
            def get_worksheet(self, idx):
                return MockWorksheet()
        
        class MockClient:
            def open_by_key(self, key):
                return MockSheet()
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test
        source = GoogleSheetsDataSource("sheet_123", creds_file, "0")
        records = source.read_records()
        
        assert len(records) == 2
        assert records[0]['name'] == 'Alice'
        assert records[1]['name'] == 'Bob'
        assert source.get_source_name() == "Test Sheet / Sheet1"
    
    def test_read_with_url_instead_of_id(self, tmp_path, monkeypatch):
        """Test reading from sheet using URL instead of ID."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create mock classes
        class MockWorksheet:
            title = 'Sheet1'
            
            def get_all_records(self):
                return [{'id': '1'}]
        
        class MockSheet:
            title = 'Test Sheet'
            
            def get_worksheet(self, idx):
                return MockWorksheet()
        
        class MockClient:
            def open_by_url(self, url):
                return MockSheet()
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test with URL
        source = GoogleSheetsDataSource(
            "https://docs.google.com/spreadsheets/d/abc123",
            creds_file,
            "0"
        )
        records = source.read_records()
        
        assert len(records) == 1
    
    def test_read_with_named_worksheet(self, tmp_path, monkeypatch):
        """Test reading from named worksheet instead of index."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create mock classes
        class MockWorksheet:
            title = 'MySheet'
            
            def get_all_records(self):
                return [{'id': '1'}]
        
        class MockSheet:
            title = 'Test Sheet'
            
            def worksheet(self, name):
                return MockWorksheet()
        
        class MockClient:
            def open_by_key(self, key):
                return MockSheet()
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test with named worksheet
        source = GoogleSheetsDataSource("sheet_123", creds_file, "MySheet")
        records = source.read_records()
        
        assert len(records) == 1
#########################################################################    
    def test_handles_spreadsheet_not_found(self, tmp_path, monkeypatch):
        """Test handling of SpreadsheetNotFound exception."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create custom exception at module level
        class SpreadsheetNotFound(Exception):
            pass
        
        # Store reference to exception
        exc_class = SpreadsheetNotFound
        
        # Create mock classes
        class MockClient:
            def open_by_key(self, key):
                raise exc_class("Spreadsheet not found")
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockExceptions:
            SpreadsheetNotFound = exc_class
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
            
            exceptions = MockExceptions
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        monkeypatch.setitem(sys.modules, 'gspread.exceptions', MockExceptions)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test - should propagate the exception
        source = GoogleSheetsDataSource("bad_sheet", creds_file, "0")
        
        with pytest.raises(exc_class):
            source.read_records()
    
    def test_handles_worksheet_not_found(self, tmp_path, monkeypatch):
        """Test handling of WorksheetNotFound exception."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create custom exception at module level
        class WorksheetNotFound(Exception):
            pass
        
        # Store reference to exception
        exc_class = WorksheetNotFound
        
        # Create mock classes
        class MockSheet:
            title = 'Test Sheet'
            
            def get_worksheet(self, idx):
                raise exc_class("Worksheet not found")
        
        class MockClient:
            def open_by_key(self, key):
                return MockSheet()
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockExceptions:
            WorksheetNotFound = exc_class
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
            
            exceptions = MockExceptions
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        monkeypatch.setitem(sys.modules, 'gspread.exceptions', MockExceptions)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test - should propagate the exception
        source = GoogleSheetsDataSource("sheet_123", creds_file, "0")
        
        with pytest.raises(exc_class):
            source.read_records()
    
    def test_handles_worksheet_by_name_not_found(self, tmp_path, monkeypatch):
        """Test handling worksheet not found when using name."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        # Create custom exception at module level
        class WorksheetNotFound(Exception):
            pass
        
        # Store reference to exception
        exc_class = WorksheetNotFound
        
        # Create mock classes
        class MockSheet:
            title = 'Test Sheet'
            
            def worksheet(self, name):
                raise exc_class(f"Worksheet '{name}' not found")
        
        class MockClient:
            def open_by_key(self, key):
                return MockSheet()
        
        class MockCredentials:
            @staticmethod
            def from_service_account_file(path, scopes):
                return MockCredentials()
        
        class MockExceptions:
            WorksheetNotFound = exc_class
        
        class MockGspread:
            @staticmethod
            def authorize(creds):
                return MockClient()
            
            exceptions = MockExceptions
        
        # Patch modules
        import sys
        monkeypatch.setitem(sys.modules, 'gspread', MockGspread)
        monkeypatch.setitem(sys.modules, 'gspread.exceptions', MockExceptions)
        
        fake_google_auth = type(sys)('google.oauth2.service_account')
        fake_google_auth.Credentials = MockCredentials
        monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', fake_google_auth)
        
        # Test with named worksheet - should propagate the exception
        source = GoogleSheetsDataSource("sheet_123", creds_file, "BadSheet")
        
        with pytest.raises(exc_class):
            source.read_records()

#################################################################################
    def test_missing_gspread_raises_import_error(self, tmp_path, monkeypatch):
        """Test that missing gspread raises helpful error."""
        # Remove gspread from modules if present
        import sys
        monkeypatch.delitem(sys.modules, 'gspread', raising=False)
        monkeypatch.delitem(sys.modules, 'google.oauth2.service_account', raising=False)
        
        # Make import fail
        def mock_import(name, *args, **kwargs):
            if 'gspread' in name or 'google.oauth2' in name:
                raise ModuleNotFoundError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)
        
        import builtins
        original_import = builtins.__import__
        monkeypatch.setattr(builtins, '__import__', mock_import)
        
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')
        
        source = GoogleSheetsDataSource("sheet_123", creds_file, "0")
        
        # Should raise ImportError with helpful message
        with pytest.raises(ImportError) as exc_info:
            source.read_records()
        
        assert "gspread and google-auth packages required" in str(exc_info.value)

class TestDataSourceFactory:
    """Tests for DataSourceFactory."""
    
    def test_create_csv_source(self, tmp_path):
        """Test creating CSV data source."""
        csv_file = tmp_path / "test.csv"
        csv_file.touch()
        
        source = DataSourceFactory.create_csv(str(csv_file))
        
        assert isinstance(source, CSVDataSource)
        assert source.filepath == csv_file
    
    def test_create_sheets_source(self, tmp_path):
        """Test creating Google Sheets data source."""
        creds_file = tmp_path / "creds.json"
        creds_file.touch()
        
        source = DataSourceFactory.create_sheets(
            "sheet_123",
            str(creds_file),
            "Sheet1"
        )
        
        assert isinstance(source, GoogleSheetsDataSource)
        assert source.sheet_id_or_url == "sheet_123"
        assert source.worksheet == "Sheet1"