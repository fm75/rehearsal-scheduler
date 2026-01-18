# Troubleshooting Flowchart

## Problem: Cannot Validate Google Sheet
```
START: Run check-constraints validate-sheet
    ↓
┌───────────────────────────────────────┐
│ Does the command exist?               │
│ (check-constraints: command not found)│
└───────────────────────────────────────┘
    │
    ├─ NO → Install package:
    │       pip install -e ".[sheets]"
    │       → RETRY
    │
    ├─ YES
    ↓
┌───────────────────────────────────────┐
│ Error: "Module gspread not found"?   │
└───────────────────────────────────────┘
    │
    ├─ YES → pip install gspread google-auth
    │        → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Error: "Credentials required"?        │
└───────────────────────────────────────┘
    │
    ├─ YES → Did you set GOOGLE_CREDENTIALS_PATH?
    │        ├─ NO → export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/credentials.json
    │        │       → RETRY
    │        └─ YES → Does the file exist?
    │                 ├─ NO → Download credentials from Google Cloud Console
    │                 │       See: docs/google-api-setup.md Step 4
    │                 │       → RETRY
    │                 └─ YES → Check file permissions:
    │                          ls -l $GOOGLE_CREDENTIALS_PATH
    │                          chmod 600 $GOOGLE_CREDENTIALS_PATH
    │                          → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Error: "Spreadsheet not found"?       │
└───────────────────────────────────────┘
    │
    ├─ YES → Is the Sheet ID correct?
    │        ├─ NO → Get ID from URL:
    │        │       https://docs.google.com/.../d/SHEET_ID/edit
    │        │       → RETRY
    │        └─ YES → Is sheet shared with service account?
    │                 ├─ NO → Share sheet with service account email
    │                 │       (found in credentials.json: "client_email")
    │                 │       Give "Viewer" permission
    │                 │       → RETRY
    │                 └─ YES → Check Sheet ID is the main document ID,
    │                          not a worksheet ID
    │                          → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Error: "API not enabled"?             │
└───────────────────────────────────────┘
    │
    ├─ YES → Enable Google Sheets API:
    │        1. Go to console.cloud.google.com
    │        2. Select your project
    │        3. APIs & Services → Library
    │        4. Search "Google Sheets API"
    │        5. Click "Enable"
    │        → Wait 1-2 minutes → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Error: "Worksheet not found"?         │
└───────────────────────────────────────┘
    │
    ├─ YES → Check worksheet name/index:
    │        ├─ Default is worksheet 0 (first sheet)
    │        ├─ Use -w "Sheet Name" for named sheets
    │        └─ Use -w 1 for second worksheet (0-indexed)
    │        → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Error: "Column not found"?            │
└───────────────────────────────────────┘
    │
    ├─ YES → Check column names in your sheet:
    │        ├─ Must have "dancer_id" column (case-sensitive)
    │        ├─ Must have "conflicts" column (case-sensitive)
    │        ├─ Check for typos or extra spaces
    │        └─ Use -c "column_name" if named differently
    │        → RETRY
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Validation runs but all tokens fail?  │
└───────────────────────────────────────┘
    │
    ├─ YES → Check constraint format:
    │        See: docs/dancer-constraints-guide.md
    │        Common issues:
    │        - Missing years on dates
    │        - Ambiguous abbreviations (use "Tu" not "T")
    │        - Invalid time formats
    │        → FIX CONSTRAINTS
    │
    ├─ NO
    ↓
┌───────────────────────────────────────┐
│ Still having issues?                  │
└───────────────────────────────────────┘
    │
    └─ YES → Debug steps:
             1. Test with single token:
                check-constraints check "W before 1 PM"
             2. Check Python version:
                python --version  (need 3.12+)
             3. Verify installation:
                pip list | grep -E "gspread|google-auth"
             4. Test credentials manually:
                python -c "from google.oauth2.service_account import Credentials; print(Credentials.from_service_account_file('$GOOGLE_CREDENTIALS_PATH'))"
             5. Check logs in pytest output
             6. Review full setup: docs/google-api-setup.md
```

---

## Quick Reference: Error Messages

| Error Message | Most Likely Cause | Quick Fix |
|---------------|-------------------|-----------|
| `command not found` | Package not installed | `pip install -e ".[sheets]"` |
| `Module gspread not found` | Missing dependencies | `pip install gspread google-auth` |
| `Credentials required` | Env var not set | `export GOOGLE_CREDENTIALS_PATH=...` |
| `Credentials file not found` | Wrong path or file doesn't exist | Check path with `ls -l` |
| `Spreadsheet not found` | Sheet not shared or wrong ID | Share with service account email |
| `API not enabled` | Sheets API not enabled in project | Enable in Cloud Console |
| `Worksheet not found` | Wrong worksheet name/index | Use `-w 0` or `-w "Sheet1"` |
| `Column not found` | Typo in column names | Check for "dancer_id" and "conflicts" |
| `Permission denied` | Wrong file permissions | `chmod 600 credentials.json` |
| `Invalid token` | Bad constraint format | See dancer-constraints-guide.md |

---

## Still Stuck?

1. **Run with verbose output**: `check-constraints validate-sheet "ID" -v`
2. **Check the detailed setup guide**: [docs/google-api-setup.md](google-api-setup.md)
3. **Verify each step** in the quick start guide above
4. **Test with a simple sheet** (2-3 rows) to isolate the issue