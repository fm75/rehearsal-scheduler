# sheet_sync.py

import gspread
import time
from process_availability import parse_dancer_availability # The function we wrote earlier

# --- Configuration ---
# The name of the downloaded JSON key file from Google Cloud
SERVICE_ACCOUNT_FILE = 'service_account.json' 

# The exact name of your Google Sheet
SHEET_NAME = 'Dancer Availability 2026'

# Columns (0-indexed, so A=0, B=1, C=2, D=3)
COL_SOURCE = 1  # Column B
COL_OUTPUT = 2  # Column C

def process_sheet():
    print("Connecting to Google Sheets...")
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open(SHEET_NAME)
    worksheet = sh.sheet1 # or sh.get_worksheet(0)

    # Get all values to minimize read calls
    # Note: efficient for small/medium sheets. For massive ones, utilize batching.
    rows = worksheet.get_all_values()
    
    # We skip the header row (index 0)
    for i in range(1, len(rows)):
        row_number = i + 1
        source_text = rows[i][COL_SOURCE]
        current_output = rows[i][COL_OUTPUT]

        # LOGIC: Only process if there is source text AND the output is empty.
        # This prevents us from overwriting existing work or reprocessing rows.
        if source_text and not current_output:
            print(f"Processing Row {row_number}: {source_text[:30]}...")
            
            try:
                # 1. Call Gemini
                compliant_string = parse_dancer_availability(source_text)
                
                # 2. Write to Sheet immediately (so you can see progress)
                # Note: 'update_cell' uses (row, col) where col is 1-based index
                worksheet.update_cell(row_number, COL_OUTPUT + 1, compliant_string)
                
                print(f"   -> {compliant_string}")
                
                # Sleep briefly to be nice to API rate limits
                time.sleep(1) 
                
            except Exception as e:
                print(f"   -> Error on row {row_number}: {e}")
        
        else:
            print(f"Skipping Row {row_number} (already done or empty)")

if __name__ == "__main__":
    process_sheet()
