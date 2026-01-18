# test/integration/test_google_sheets.py

import pytest
import os
from pathlib import Path

# Debug: show what pytest-dotenv is finding
# print(f"DEBUG: Current dir = {os.getcwd()}")
# print(f"DEBUG: .env exists = {Path('.env').exists()}")
# print(f"DEBUG: GOOGLE_TEST_CREDENTIALS = {os.getenv('GOOGLE_TEST_CREDENTIALS')}")
# print(f"DEBUG: GOOGLE_TEST_SHEET_ID = {os.getenv('GOOGLE_TEST_SHEET_ID')}")

# Skip if credentials not available
CREDENTIALS_PATH = os.getenv(
    'GOOGLE_TEST_CREDENTIALS',
    str(Path.home() / '.config/rehearsal-scheduler/test-credentials.json')
)
TEST_SHEET_ID = os.getenv('GOOGLE_TEST_SHEET_ID', None)

skip_if_no_credentials = pytest.mark.skipif(
    not Path(CREDENTIALS_PATH).exists() or not TEST_SHEET_ID,
    reason="Google credentials or sheet ID not configured"
)

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

skip_if_no_gspread = pytest.mark.skipif(
    not GSPREAD_AVAILABLE,
    reason="gspread not installed (pip install gspread google-auth)"
)


@skip_if_no_gspread
@skip_if_no_credentials
class TestGoogleSheetsIntegration:
    """Integration tests using a real Google Sheet."""
    
    @pytest.fixture
    def sheet_client(self):
        """Connect to Google Sheets."""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
        return gspread.authorize(creds)
    
    def test_can_connect_to_test_sheet(self, sheet_client):
        """Verify we can connect to the test sheet."""
        sheet = sheet_client.open_by_key(TEST_SHEET_ID)
        assert sheet is not None
        assert sheet.title is not None
        print(f"Connected to sheet: {sheet.title}")
    
    def test_can_read_test_data(self, sheet_client):
        """Verify we can read data from the test sheet."""
        sheet = sheet_client.open_by_key(TEST_SHEET_ID)
        ws = sheet.get_worksheet(0)
        records = ws.get_all_records()
        
        assert len(records) > 0
        assert 'dancer_id' in records[0]
        assert 'conflicts' in records[0]
    
    def test_validate_test_sheet_data(self, sheet_client):
        """Run validation on test sheet data."""
        from rehearsal_scheduler.check_constraints import validate_records
        
        sheet = sheet_client.open_by_key(TEST_SHEET_ID)
        ws = sheet.get_worksheet(0)
        records = ws.get_all_records()
        
        error_records, stats = validate_records(
            records,
            id_column='dancer_id',
            column='conflicts',
            verbose=False,
            source_name='test sheet'
        )
        
        # Should have some valid and some invalid tokens based on our test data
        assert stats is not None
        assert stats['total_rows'] == 7  # Based on test data above
        assert stats['valid_tokens'] > 0
        assert stats['invalid_tokens'] == 2  # "invalid text here" and "T after 12:15"
        assert len(error_records) == 2
        
        # Check specific error
        invalid_dancers = {e['dancer_id'] for e in error_records}
        assert 'd_002' in invalid_dancers  # "invalid text here"
        assert 'd_005' in invalid_dancers  # "T after 12:15" (ambiguous)