/**
 * DANCE SCHEDULER - AVAILABILITY PARSER (FEW-SHOT VERSION)
 * * context:   Parses natural language availability into strict constraints.
 * repo:      [https://github.com/fm75/rehearsal-scheduler]
 * author:    [Fred Mitchell]
 */

const API_KEY = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
const MODEL_NAME = 'gemini-2.5-pro'; 
const HEADERS = { SOURCE: 'raw_constraints_from_form', OUTPUT: 'ai_translation' };
const DEFAULT_YEAR = 2026;

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Dance Tools').addItem('Process Availability', 'processRows').addToUi();
}

function processRows() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  
  if (lastRow < 2) return;
  if (!API_KEY) { SpreadsheetApp.getUi().alert("Error: GEMINI_API_KEY missing."); return; }

  const headerValues = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const colSource = headerValues.indexOf(HEADERS.SOURCE);
  const colOutput = headerValues.indexOf(HEADERS.OUTPUT);

  if (colSource === -1 || colOutput === -1) { SpreadsheetApp.getUi().alert("Error: Missing headers."); return; }

  const data = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
  
  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    if (row[colSource] && !row[colOutput]) {
      try {
        const result = callGemini(row[colSource]);
        sheet.getRange(i + 2, colOutput + 1).setValue(result);
        SpreadsheetApp.flush(); 
      } catch (e) {
        sheet.getRange(i + 2, colOutput + 1).setValue("Error: " + e.message);
      }
    }
  }
}

/**
 * Calls Gemini using "Few-Shot Prompting" (Examples) instead of a Markdown Manual.
 */
function callGemini(text) {
  
  // 1. STRICT LARK GRAMMAR (The Output Schema)
  const LARK_GRAMMAR = `
    start: constraint ("," constraint)*
    constraint: temporal_constraint | date_constraint

    temporal_constraint: day_spec (time_spec)?
    day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY
    time_spec: after_spec | before_spec | time_range
    after_spec: "after"i tod
    before_spec: ("before"i | "until"i) tod
    time_range: tod "-" tod
    tod: std_time | military_time
    std_time: HOUR (":" MINUTE)? AM_PM?
    military_time: MILITARY_TIME

    date_constraint: date_value (time_spec)? | date_value ("-" date_value)?
    date_value: mdy_slash | mdy_text
    mdy_slash: MONTH_NUM "/" DAY_NUM "/" YEAR
    mdy_text: MONTH_TEXT DAY_NUM YEAR
        
    MILITARY_TIME.2: /([01][0-9]|2[0-3])[0-5][0-9]/    
    HOUR.1: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12"
    MINUTE: "00" | "01" | "02" | "03" | "04" | "05" | "06" | "07" | "08" | "09" 
          | "10" | "11" | "12" | "13" | "14" | "15" | "16" | "17" | "18" | "19" 
          | "20" | "21" | "22" | "23" | "24" | "25" | "26" | "27" | "28" | "29" 
          | "30" | "31" | "32" | "33" | "34" | "35" | "36" | "37" | "38" | "39" 
          | "40" | "41" | "42" | "43" | "44" | "45" | "46" | "47" | "48" | "49" 
          | "50" | "51" | "52" | "53" | "54" | "55" | "56" | "57" | "58" | "59"
    AM_PM: "am"i | "pm"i
    MONDAY:    "monday"i    | "mon"i   | "mo"i | "m"i
    TUESDAY:   "tuesday"i   | "tues"i  | "tu"i
    WEDNESDAY: "wednesday"i | "wed"i   | "we"i | "w"i
    THURSDAY:  "thursday"i  | "thurs"i | "th"i
    FRIDAY:    "friday"i    | "fri"i   | "fr"i | "f"i
    SATURDAY:  "saturday"i  | "sat"i   | "sa"i
    SUNDAY:    "sunday"i    | "sun"i   | "su"i
    MONTH_TEXT.2: /(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)/i
    YEAR.1: /\\d{4}|\\d{2}/
    MONTH_NUM.1: /1[0-2]|0?[1-9]/
    DAY_NUM.1: /[12][0-9]|3[01]|0?[1-9]/
    %import common.WS
    %ignore WS
  `;

  // 2. TRAINING EXAMPLES (The "Gold Standard" logic)
  // This explicitly teaches the AI how to handle the tricky cases without needing a manual.
  const FEW_SHOT_EXAMPLES = `
    Input: "Monday"
    Output: Monday

    Input: "I can't do Tuesdays"
    Output: Tuesday

    Input: "Wed before 6"
    Output: Wed before 6:00 pm

    Input: "Thursday after 9"
    Output: Thursday after 9:00 pm

    Input: "Fri 12 - 2"
    Output: Fri 12:00 pm - 2:00 pm

    Input: "Jan 20 26"
    Output: Jan 20 26

    Input: "Dec 20 25 - Dec 28 25"
    Output: Dec 20 25 - Dec 28 25

    Input: "Feb 2 before 1pm"
    Output: Feb 2 26 before 1:00 pm

    Input: "M before 5, Jan 15"
    Output: Mon before 5:00 pm, Jan 15 26
  `;

  const systemPrompt = `
    You are a parsing engine. 
    Convert the Input into a string that strictly matches the LARK GRAMMAR.

    ### CONTEXT
    - Dancers are 55+ (retired/working mixed).
    - "Before 6" usually means PM.
    - "After 5" always means PM.
    - The input was their natural language response to a request for when they would not be available to rehearse.

    ### LARK GRAMMAR
    ${LARK_GRAMMAR}

    ### EXAMPLES
    ${FEW_SHOT_EXAMPLES}

    ### CRITICAL
    - Output ONLY the result string.
    - If you are not sure what the input means, return "NO IDEA".
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

  if (json.error) throw new Error(json.error.message);

  if (json.candidates && json.candidates[0].content) {
    return json.candidates[0].content.parts[0].text.replace(/```/g, "").trim();
  } else {
    return "NO IDEA"; 
  }
}