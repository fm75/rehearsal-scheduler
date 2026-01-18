# Google Sheets API Setup Guide

This guide walks through setting up Google Cloud credentials to access Google Sheets for constraint validation.

## Overview

The `check-constraints` tool can validate dancer availability constraints directly from Google Sheets. This requires:
1. A Google Cloud project with Sheets API enabled
2. A service account with credentials
3. Sharing your sheet with the service account

## Prerequisites

- A Google account (personal or Google Workspace)
- Access to the Google Sheets you want to validate
- Ability to create Google Cloud projects (free tier is sufficient)

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click the project dropdown at the top of the page
4. Click **"New Project"**
5. Enter project details:
   - **Project name**: `rehearsal-scheduler` (or your preference)
   - **Organization**: Choose your organization if using Google Workspace, or leave as "No organization"
6. Click **"Create"**
7. Wait for the project to be created (you'll see a notification)

---

## Step 2: Enable Google Sheets API

1. In the Google Cloud Console, ensure your new project is selected (check the dropdown at the top)
2. Open the navigation menu (☰) → **APIs & Services** → **Library**
3. In the search box, type: `Google Sheets API`
4. Click on **Google Sheets API** in the results
5. Click **"Enable"**
6. Wait for the API to be enabled

---

## Step 3: Create a Service Account

A service account is a special type of account that represents an application rather than a person.

1. Open the navigation menu (☰) → **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** at the top
3. Select **"Service Account"**
4. Fill in the service account details:
   - **Service account name**: `rehearsal-validator` (or your preference)
   - **Service account ID**: Auto-generated (e.g., `rehearsal-validator@your-project.iam.gserviceaccount.com`)
   - **Description**: "Service account for validating rehearsal constraints"
5. Click **"Create and Continue"**
6. **Grant this service account access to project** (optional):
   - You can skip this by clicking **"Continue"**
7. **Grant users access to this service account** (optional):
   - You can skip this by clicking **"Done"**

---

## Step 4: Create and Download Credentials

1. On the **Credentials** page, find your service account in the **Service Accounts** section
2. Click on the service account email (e.g., `rehearsal-validator@your-project.iam.gserviceaccount.com`)
3. Go to the **Keys** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **JSON** format
6. Click **"Create"**
7. A JSON file will automatically download to your computer
8. **Important**: Keep this file secure! It provides access to your Google Cloud resources

---

## Step 5: Store Credentials Securely

### On the Raspberry Pi (or Linux/Mac)
```bash
# Create a secure directory for credentials
mkdir -p ~/.config/rehearsal-scheduler

# Move the downloaded JSON file (adjust path as needed)
mv ~/Downloads/your-project-*.json ~/.config/rehearsal-scheduler/credentials.json

# Set restrictive permissions (only you can read)
chmod 600 ~/.config/rehearsal-scheduler/credentials.json

# Verify the file exists
ls -l ~/.config/rehearsal-scheduler/credentials.json
```

### Important Security Notes

- **Never commit credentials to git!** Add to `.gitignore`:
```bash
  echo "*.json" >> .gitignore
  echo "credentials.json" >> .gitignore
```
- **Don't share the JSON file** - it grants access to Google Cloud resources
- **Keep backups** in a secure location (encrypted storage, password manager, etc.)

---

## Step 6: Share Your Google Sheet with the Service Account

The service account needs permission to read your Google Sheet.

1. Open your Google Sheet (the one with dancer constraints)
2. Click the **"Share"** button (top right)
3. In the "Add people and groups" field, paste the **service account email**
   - Find this in the downloaded JSON file: look for `"client_email"`
   - Or find it in Google Cloud Console → IAM & Admin → Service Accounts
   - Example: `rehearsal-validator@your-project.iam.gserviceaccount.com`
4. Set permission level: **Viewer** (read-only is sufficient)
5. **Uncheck** "Notify people" (the service account doesn't need an email notification)
6. Click **"Share"** or **"Done"**

---

## Step 7: Test the Connection

### Find Your Sheet ID

Your Google Sheets URL looks like:
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

Copy the `SHEET_ID_HERE` portion.

### Test with the CLI
```bash
# Navigate to your project directory
cd /data/rehearsal-scheduler
source venv/bin/activate

# Test the connection
check-constraints validate-sheet "YOUR_SHEET_ID" \
  -k ~/.config/rehearsal-scheduler/credentials.json

# Or set an environment variable
export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/credentials.json
check-constraints validate-sheet "YOUR_SHEET_ID"
```

If successful, you should see:
```
Connected to: Your Sheet Name
Worksheet: Sheet1
Validating constraints from: Your Sheet Name / Sheet1
...
```

---

## Environment Variables (Optional but Recommended)

To avoid typing the credentials path every time:

### Temporary (current session only)
```bash
export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/credentials.json
```

### Permanent (add to ~/.bashrc)
```bash
echo 'export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/credentials.json' >> ~/.bashrc
source ~/.bashrc
```

Now you can run without the `-k` flag:
```bash
check-constraints validate-sheet "YOUR_SHEET_ID"
```

---

## Testing Setup

For running integration tests:

1. Create a test Google Sheet with sample data
2. Share it with your service account
3. Set environment variables:
```bash
   export GOOGLE_TEST_CREDENTIALS=~/.config/rehearsal-scheduler/credentials.json
   export GOOGLE_TEST_SHEET_ID="your_test_sheet_id"
```

4. Or add to `.env` file in project root:
```bash
   GOOGLE_TEST_CREDENTIALS=/home/fred/.config/rehearsal-scheduler/credentials.json
   GOOGLE_TEST_SHEET_ID=your_test_sheet_id
```

5. Run tests:
```bash
   pytest test/integration/test_google_sheets.py -v
```

---

## Multiple Environments (Development vs Production)

If you're working with multiple Google accounts (e.g., personal and workspace):

### Development (Personal Account)
```bash
~/.config/rehearsal-scheduler/dev-credentials.json
export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/dev-credentials.json
```

### Production (Organization Account)
```bash
~/.config/rehearsal-scheduler/prod-credentials.json
export GOOGLE_CREDENTIALS_PATH=~/.config/rehearsal-scheduler/prod-credentials.json
```

Switch between them by changing the environment variable.

---

## Troubleshooting

### "Spreadsheet not found or not accessible"

**Problem**: The service account doesn't have access to the sheet.

**Solution**:
1. Verify you shared the sheet with the correct service account email
2. Check that you gave "Viewer" or "Editor" permissions
3. Make sure you're using the correct Sheet ID

### "Credentials file not found"

**Problem**: The path to credentials is incorrect.

**Solution**:
```bash
# Verify the file exists
ls -l ~/.config/rehearsal-scheduler/credentials.json

# Check the path you're using
echo $GOOGLE_CREDENTIALS_PATH
```

### "API has not been used in project... before or it is disabled"

**Problem**: Google Sheets API is not enabled for your project.

**Solution**: Go back to Step 2 and enable the Google Sheets API.

### "Permission denied" when reading credentials file

**Problem**: File permissions are too restrictive or you don't own the file.

**Solution**:
```bash
# Fix ownership
sudo chown $USER:$USER ~/.config/rehearsal-scheduler/credentials.json

# Fix permissions
chmod 600 ~/.config/rehearsal-scheduler/credentials.json
```

---

## Security Best Practices

1. **Principle of Least Privilege**: Only share sheets with the service account that need validation
2. **Read-Only Access**: Give service accounts "Viewer" permission, not "Editor"
3. **Audit Access**: Periodically review which sheets are shared with service accounts
4. **Rotate Credentials**: If credentials are compromised:
   - Delete the key in Google Cloud Console
   - Create a new key
   - Update your local credentials file
5. **Monitor Usage**: Check Google Cloud Console for unexpected API usage

---

## Cost

- **Google Sheets API**: Free tier includes 500 requests per 100 seconds per project
- **Google Cloud Project**: Free (no charges for basic API usage)
- **Service Account**: Free

For typical rehearsal scheduling (validating one sheet with 50 dancers a few times per week), you'll stay well within the free tier.

---

## Additional Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Service Accounts Overview](https://cloud.google.com/iam/docs/service-accounts)
- [Google Cloud Console](https://console.cloud.google.com/)
- [gspread Python Library Documentation](https://docs.gspread.org/)

---

## Summary Checklist

- [ ] Create Google Cloud project
- [ ] Enable Google Sheets API
- [ ] Create service account
- [ ] Download JSON credentials
- [ ] Store credentials securely on your system
- [ ] Share your Google Sheet with service account email
- [ ] Set `GOOGLE_CREDENTIALS_PATH` environment variable
- [ ] Test connection with `check-constraints validate-sheet`
- [ ] Add credentials path to `.gitignore`

Once complete, you can validate constraints directly from Google Sheets!