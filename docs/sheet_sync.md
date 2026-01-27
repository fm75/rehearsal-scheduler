# Gemini Translation of Constraints
## From Natural Language to Constraint Grammar
This is a classic "enrichment" workflow. We can write a script that reads your "Source" column, sends the text to Gemini (using the function we just wrote), and writes the result into a "Gemini Suggestion" column.

You can then review the suggestions and copy/edit them into your final "Truth" column.

### Prerequisite: Google Cloud Setup

To touch Google Sheets with Python, you need a Service Account. It sounds scary, but it's just a robot user.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (e.g., "Dance Scheduler").
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Create a **Service Account**, give it "Editor" access, and download the **JSON key file**.
5. **Important:** Open your actual Google Sheet in your browser, click "Share," and paste the `client_email` found inside that JSON file. This gives the robot permission to see your sheet.

### The Script (`sheet_sync.py`)

You will need to install `gspread` to talk to Sheets:

```bash
pip install gspread google-auth

```

Here is the script. It assumes your Sheet looks like this:

* **Column A:** Dancer Name (optional, for reference)
* **Column B:** Natural Language Input (The Source)
* **Column C:** Gemini Suggestion (Where we write)
* **Column D:** Truth (Final constraints for your code)



### The Workflow

1. **Run the script:** It will scan down the list. If it sees text in Column B but nothing in Column C, it sends it to Gemini and fills in Column C.
2. **Review:** You open the Sheet.
* If Gemini got it right (which it did for most of our tests), you just copy Column C to Column D ("Truth").
* If Gemini got it wrong (like the "Work till 12:00" ambiguity), you manually type the correct version into Column D.


3. **Final Export:** Your scheduling code will eventually just read Column D, ignoring the messy human text and the robot helper columns.

Would you like me to adjust the script to automatically copy the Gemini answer into the "Truth" column as well, or do you prefer the safety of doing that manually?