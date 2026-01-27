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


## 4. Usage

1. Reload your Google Sheet.
2. Wait a few seconds for the **Dance Tools** menu to appear in the toolbar.
3. Click **Dance Tools > Process Availability**.
4. *First Run Only:* Grant permissions for the script to edit the sheet and connect to external services (Google Gemini).