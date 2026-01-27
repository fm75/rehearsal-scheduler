import os
import google.generativeai as genai
from pathlib import Path

# --- Configuration ---
CONFIG_FILE = ".gemini"
CONTEXT_FILE = "dancer-constraints-guide.md" # The markdown file you uploaded
GRAMMAR_FILE = "grammar.py" # Useful to include strict rules if needed

def load_config():
    """Simple parser for .gemini config file (KEY=VALUE)."""
    config = {}
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Could not find {CONFIG_FILE}")
    
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()
    return config

def load_file_content(filename):
    """Reads text content from a file."""
    try:
        return Path(filename).read_text()
    except FileNotFoundError:
        return f"Error: {filename} not found."

def get_system_instruction():
    """Combines the Markdown guide and Grammar file into a master instruction."""
    guide = load_file_content(CONTEXT_FILE)
    grammar = load_file_content(GRAMMAR_FILE)
    
    return f"""
    You are a parsing assistant for a dance company scheduler.
    Your goal is to convert natural language text messages from dancers into strict constraint strings defined by our Python grammar.

    ### REFERENCE 1: The User Guide
    {guide}

    ### REFERENCE 2: The Formal Grammar (Python)
    {grammar}

    ### INSTRUCTIONS
    1. Output ONLY the compliant string.
    2. If the input cannot be parsed or contradicts the rules, output "NO IDEA".
    3. Assume the current year is 2026.
    4. Do not explain your reasoning. Just the string.
    """

def parse_dancer_availability(dancer_text):
    config = load_config()
    genai.configure(api_key=config.get("API_KEY"))
    
    # Initialize the model
    model = genai.GenerativeModel(
        model_name=config.get("DEFAULT_MODEL", "gemini-1.5-pro"),
        system_instruction=get_system_instruction()
    )

    # Pre-load the few-shot examples we just created to enforce behavior
    # This teaches the model the "User -> Correct Output" pattern
    history = [
        {
            "role": "user",
            "parts": ["April 18-30 out"]
        },
        {
            "role": "model",
            "parts": ["Apr 18 26 - Apr 30 26"]
        },
        {
            "role": "user",
            "parts": ["Away Feb.20 - March 14"]
        },
        {
            "role": "model",
            "parts": ["Feb 20 26 - Mar 14 26"]
        },
        {
            "role": "user",
            "parts": ["Camelot show March 22 24 25 26 Camelot rehearsal on Wednesdays until 1:00 pm on March 4 11 18"]
        },
        {
            "role": "model",
            "parts": ["Mar 22 26, Mar 24 26, Mar 25 26, Mar 26 26, Mar 4 26 until 1:00 PM, Mar 11 26 until 1:00 PM, Mar 18 26 until 1:00 PM"]
        }
    ]

    # Start chat with history
    chat = model.start_chat(history=history)
    
    # Send the actual new request
    response = chat.send_message(dancer_text)
    
    return response.text.strip()

# --- Example Usage ---
if __name__ == "__main__":
    # Test with a messy input
    incoming_text = "I can't do Mondays or Jan 5, also out Feb 10-12 for a trip."
    
    print(f"Input: {incoming_text}")
    print("Parsing...")
    
    try:
        result = parse_dancer_availability(incoming_text)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")