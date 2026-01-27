# Porting to An Organization Environment
Porting from a personal environment to an organizational Workspace  is a smart move for longevity, but there are a few specific "gotchas" with Google Apps Script and Cloud Projects.

Here is your checklist for a smooth migration.

### 1. The "Bus Factor" (File Ownership)

**The Pitfall:** If you create the Sheet in your personal Gmail and just share it with the Director, and one day your personal storage fills up, or you get locked out, or you delete the file by mistake, the organization loses its data.
**The Fix:** Use **Shared Drives**.

* **Create a Shared Drive** inside `YOURORG.org` (e.g., "Production Planning").
* Move the Sheet into that Shared Drive.
* **Why:** Files in a Shared Drive are owned by the *organization*, not a specific person. If you leave or your account is deleted, the file stays there.

### 2. The API Key (The "Brains")

**The Pitfall:** If you use the API key from your personal `gmail.com` Google Cloud project, you are personally liable for the usage. If the script goes haywire and hits a billing limit, it hits *your* credit card (if configured). Also, it violates data governance principles (sending org data to a personal project).
**The Fix:** Create a new GCP Project.

1. Log in to Google Cloud Console as your **organizational user** (e.g., `you@YOURORG.org`).
2. Create a new Project (e.g., `YOURORG-dance-scheduler`).
3. Enable the **Generative Language API** (Gemini) in that new project.
4. Generate a **NEW API Key**.
5. Update the **Script Properties** in the Sheet to use this new key.

### 3. "Unverified App" Warnings (User Experience)

**The Scenario:** You set everything up. the Director logs in, opens the menu, and clicks "Process Availability."
**The Pitfall:** She sees a scary red screen saying **"This app isn't verified."**
**The Reality:** This happens because the script is calling an external URL (the Gemini API) and hasn't been "published" to the Google Marketplace.
**The Fix:**

* **Don't Panic:** Tell the Director this is normal for internal tools.
* **The Click Path:** She needs to click **"Advanced"** (small text) -> **"Go to [Script Name] (unsafe)"**.
* She only has to do this **once**. After that, it's authorized.

### 4. Quotas and Billing

**The Pitfall:** Getting a surprise bill.
**The Reality:**

* **Gemini 1.5 Flash** is currently free-to-use within generous rate limits (15 RPM, 1M TPM). A dance studio scheduling ~50 dancers once a season will nowhere near hit this.
* **Google Workspace Quotas:** Standard Google accounts have limits on how many usage calls `UrlFetchApp` can make per day (20,000 calls/day for Workspace accounts). You are safe here.
* **Subscription:** You generally **do not** need to attach a billing account (credit card) to the GCP project if you stay within the free tier of the Gemini API. However, to prevent service interruption, the org usually adds a card with a $0 budget alert.

### 5. Deployment Strategy (Clasp vs. Copy)

Since you are the sole developer:

* **Option A (Easy):** Just copy/paste the final code into the script editor of the "Live" sheet in the Shared Drive.
* **Option B (Pro):** Use `clasp`.
1. Create a `.clasp.json` that points to the **Script ID** of the Live Sheet.
2. When you make updates in your local Jupyter environment, you `clasp push` to deploy them to the live sheet.


* *Note:* You can have a `prod` branch in git and a `dev` branch. `prod` pushes to the live sheet ID; `dev` pushes to a test sheet ID.



### Summary Checklist for "Go Live"

1. [ ] **Create Shared Drive** in `YOURORG.org`.
2. [ ] **Move/Copy Sheet** there.
3. [ ] **Create GCP Project** under `YOURORG.org` account.
4. [ ] **Generate New API Key** in that project.
5. [ ] **Add API Key** to Script Properties in the Live Sheet.
6. [ ] **Run it once yourself** to authorize it.
7. [ ] **Walk the Director through** the "Unverified App" screen for her first run.

Would you like a template for an email to send to the Director explaining how to use the "Process Availability" button and the warning screen?