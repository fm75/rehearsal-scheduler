# Quick Start: Google Sheets Validation

Get up and running with Google Sheets constraint validation in 10 minutes.

## Prerequisites

- [ ] Google account (personal or workspace)
- [ ] Google Sheet with `dancer_id` and `conflicts` columns
- [ ] 10 minutes

---

## Quick Setup (5 Steps)

### 1. Create Google Cloud Project (2 min)

1. Go to: https://console.cloud.google.com/
2. Click "New Project"
3. Name it: `rehearsal-scheduler`
4. Click "Create"

### 2. Enable API (1 min)

1. Search for: `Google Sheets API`
2. Click "Enable"

### 3. Create Service Account (2 min)

1. Go to: APIs & Services → Credentials
2. Click: "+ Create Credentials" → "Service Account"
3. Name: `rehearsal-validator`
4. Click: "Create and Continue" → "Done"

### 4. Get Credentials (1 min)

1. Click on your new service account email
2. Go to "Keys" tab
3. Click: "Add Key" → "Create new key" → "JSON"
4. Save the downloaded file

### 5. Share Your Sheet (1 min)

1. Open your Google Sheet
2. Click "Share"
3. Paste the service account email (from the JSON file: `client_email`)
4. Set to "Viewer"
5. Uncheck "Notify people"
6. Click "Share"

---

## Installation on Raspberry Pi
```bash
# Install the package with Google Sheets support
cd /data/rehearsal-scheduler
source venv/bin/activate
pip install -e ".[sheets]"

# Store credentials
mkdir -p ~/.config/rehearsal-scheduler
mv ~/Downloads/your-credentials-*.json ~/.config/rehearsal-scheduler/credentials.json
chmod 600 ~/.config/rehearsal-scheduler/credentials.json

# Set environment variable
echo 'export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/credentials.json' >> ~/.bashrc
source ~/.bashrc
```

---

## First Validation
```bash
# Get your Sheet ID from the URL:
# https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit

# Run validation
check-constraints validate-sheet "YOUR_SHEET_ID"
```

### Expected Output
```
Connected to: Your Sheet Name
Worksheet: Sheet1
Validating constraints from: Your Sheet Name / Sheet1
======================================================================

✓ d_001 [token 1]: W before 1 PM
✓ d_002 [token 1]: M
✓ d_002 [token 2]: Tu after 5 PM
❌ d_003 (row 4, token 1):
   Token: 'invalid text'
   ...

======================================================================
SUMMARY
----------------------------------------------------------------------
Total dancers:        10
Empty constraints:    2
Total tokens:         15
Valid tokens:         13 ✓
Invalid tokens:       2 ❌
Success rate:         86.7% ⚠
```

---

## Common First-Time Issues

### "Spreadsheet not found"
→ **Did you share the sheet with the service account?**
   - Open your sheet → Share
   - Add the service account email (ends in `@*.iam.gserviceaccount.com`)

### "Credentials file not found"
→ **Check the path:**
```bash
ls -l ~/.config/rehearsal-scheduler/credentials.json
echo $GOOGLE_CREDENTIALS_PATH
```

### "Module gspread not found"
→ **Install with sheets support:**
```bash
pip install -e ".[sheets]"
```

---

## Next Steps

Once validation works:

1. **Fix invalid constraints** in your Google Sheet
2. **Re-run validation** until 100% success rate
3. **Set up for director**: Share credentials and Sheet ID
4. **Automate**: Run validation before each scheduling session

---

## Sheet Format Requirements

Your Google Sheet must have these columns:

| dancer_id | conflicts |
|-----------|-----------|
| d_001     | W before 1 PM |
| d_002     | M, Tu after 5 PM |
| d_003     | Jan 20 26 - Jan 25 26 |

Column names must match exactly (case-sensitive):
- `dancer_id` - unique identifier for each dancer
- `conflicts` - comma-separated constraint tokens

---

## Help

For detailed setup instructions, see: [docs/google-api-setup.md](google-api-setup.md)

For constraint format help, see: [docs/dancer-constraints-guide.md](dancer-constraints-guide.md)