Here is the `docs/google_apps_script_setup.md` file you requested.

This guide treats your code as "GitHub ready" (no hardcoded secrets) while acknowledging that you might not want to install a full Node.js pipeline immediately. You can simply save the code below into your repo (e.g., as `gas/Code.js`) to version control it, even if you copy-paste it into the Google editor for now.

---

# Google Apps Script Setup

This document details how to set up the Google Sheets integration for the Dance Scheduler. The script uses Google's Gemini API to parse natural language constraints into strict data formats.

## 1. Prerequisites

### A. Google Gemini API Key

1. Go to [Google AI Studio (aai.google.dev)](https://www.google.com/search?q=https://aai.google.dev/).
2. Click **Get API key** in the top left.
3. Click **Create API key in new project**.
4. Copy the key string (starts with `AIza...`).
* *Security Note:* **Never** commit this key to GitHub or paste it directly into the code.



### B. Google Sheet Preparation

1. Open your **Dancer Availability** Google Sheet.
2. Ensure Row 1 contains the following specific headers (case-sensitive):
* `constraints` (The input text from the dancers)
* `ai_translation` (Where the script will write the output)



---

## 2. Installing the Script

### Option A: Manual Installation (Quickest)

1. Open your Google Sheet.
2. Go to **Extensions > Apps Script**.
3. Delete any existing code in the editor.
4. Copy and paste the **Script Code** provided below.
5. Click the **Save** icon (Floppy disk).

### Option B: Local Development (Advanced)

If you wish to sync this directly from your local environment (Mac M2) to Google, you will need **Node.js** and **CLASP**.

1. Install Node.js on your Mac.
2. Install CLASP: `npm install -g @google/clasp`
3. Login: `clasp login`
4. Clone your script: `clasp clone "YOUR_SCRIPT_ID"` (Found in Apps Script Project Settings).
5. Push changes: `clasp push`

---

## 3. Configuring the API Key (Critical Step)

Since the code is "GitHub Ready," it does not contain your API key. You must inject it securely via the Google Apps Script environment.

1. In the Apps Script Editor, click the **Project Settings** (Gear icon) on the left sidebar.
2. Scroll down to the **Script Properties** section.
3. Click **Add script property**.
4. Enter the following:
* **Property:** `GEMINI_API_KEY`
* **Value:** `[Paste your AIza... key here]`


5. Click **Save script properties**.

---

## 4. The Script Code (`gas/Code.js`)

Save this file in your GitHub repository (e.g., `src/gas/Code.js`).

```javascript
/**
 * DANCE SCHEDULER - AVAILABILITY PARSER
 * * context:   Parses natural language availability into strict constraints.
 * repo:      [Your Repo URL]
 * author:    [Your Name]
 */

// --- CONFIGURATION ---
// We fetch the key securely from Script Properties to avoid committing secrets to GitHub.
const API_KEY = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
const MODEL_NAME = 'gemini-1.5-flash';

// The headers in the Google Sheet (Row 1) to map inputs and outputs.
const HEADERS = {
  SOURCE: 'constraints',       // Input column
  OUTPUT: 'ai_translation',    // Output column
};

// Context for the AI to resolve ambiguous dates
const DEFAULT_YEAR = 2026;

/**
 * Adds the menu item to the Google Sheet UI on load.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Dance Tools')
    .addItem('Process Availability', 'processRows')
    .addToUi();
}

/**
 * Main function to read rows, call API, and write results.
 */
function processRows() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  
  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert("No data found to process.");
    return; 
  }

  // 1. Validation: Check for API Key
  if (!API_KEY) {
    SpreadsheetApp.getUi().alert(
      "Error: GEMINI_API_KEY not found.\n\nPlease go to Project Settings > Script Properties and add your API key."
    );
    return;
  }

  // 2. Find Column Indices based on Headers
  const headerValues = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const colSourceIndex = headerValues.indexOf(HEADERS.SOURCE);
  const colOutputIndex = headerValues.indexOf(HEADERS.OUTPUT);

  if (colSourceIndex === -1 || colOutputIndex === -1) {
    SpreadsheetApp.getUi().alert(
      `Error: Could not find columns named "${HEADERS.SOURCE}" or "${HEADERS.OUTPUT}". Please check row 1 headers.`
    );
    return;
  }

  // 3. Process Data
  // We get the full data range (excluding header)
  const dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
  const data = dataRange.getValues();
  
  // Iterate through rows
  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    const sourceText = row[colSourceIndex];
    const currentOutput = row[colOutputIndex];
    
    // LOGIC: Only process if Source exists AND Output is empty
    if (sourceText && !currentOutput) {
      try {
        const result = callGemini(sourceText);
        
        // Write result back to sheet
        // (i + 2) accounts for 0-based index and the header row
        sheet.getCell(i + 2, colOutputIndex + 1).setValue(result);
        
        // Force UI update so user sees progress
        SpreadsheetApp.flush(); 
        
      } catch (e) {
        sheet.getCell(i + 2, colOutputIndex + 1).setValue("Error: " + e.message);
      }
    }
  }
}

/**
 * Calls the Google Gemini API.
 */
function callGemini(text) {
  const systemPrompt = `
    You are a parsing assistant for a dance company.
    Convert natural language text into strict constraint strings.
    
    CONTEXT:
    - The current production year is ${DEFAULT_YEAR}.
    - If a month is mentioned without a year (e.g., "March 12"), assume ${DEFAULT_YEAR}.
    - If the user explicitly mentions a different year (e.g., "Jan 2027"), respect it.

    RULES:
    1. Output ONLY the compliant string.
    2. If the input cannot be parsed or contradicts rules, output "NO IDEA".
    3. Use 3-letter months (Jan, Feb, Mar).
    4. Dates MUST include the year: "Mar 4 ${DEFAULT_YEAR % 100}".
    5. Ranges: "Date - Date".
    6. Times: "until 1:00 PM", "after 2:00 PM", "before 12:00 PM".

    EXAMPLES:
    Input: April 18-30 out
    Output: Apr 18 ${DEFAULT_YEAR % 100} - Apr 30 ${DEFAULT_YEAR % 100}

    Input: Camelot show March 22 24 25
    Output: Mar 22 ${DEFAULT_YEAR % 100}, Mar 24 ${DEFAULT_YEAR % 100}, Mar 25 ${DEFAULT_YEAR % 100}
  `;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL_NAME}:generateContent?key=${API_KEY}`;
  
  const payload = {
    "contents": [
      {
        "parts": [
          {"text": systemPrompt},
          {"text": "Input: " + text}
        ]
      }
    ]
  };

  const options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };

  const response = UrlFetchApp.fetch(url, options);
  const json = JSON.parse(response.getContentText());

  if (json.error) {
    throw new Error(json.error.message);
  }

  if (json.candidates && json.candidates[0].content) {
    return json.candidates[0].content.parts[0].text.trim();
  } else {
    return "NO IDEA"; 
  }
}

```

## 5. Usage

1. Reload your Google Sheet.
2. Wait a few seconds for the **Dance Tools** menu to appear in the toolbar.
3. Click **Dance Tools > Process Availability**.
4. *First Run Only:* Grant permissions for the script to edit the sheet and connect to external services (Google Gemini).