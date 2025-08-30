import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()

# --- Load BOTH API Keys ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Define BOTH Service Endpoints ---
GRANITE_API_URL = "https://api-inference.huggingface.co/models/ibm-granite/granite-3.3-2b-instruct"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

GOOGLE_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
GOOGLE_HEADERS = {"Content-Type": "application/json"}


def _query_granite_for_extraction(text: str) -> list | None:
    """Attempts to extract data using the IBM Granite model. Returns None on failure."""
    if not HF_API_TOKEN:
        print("Hugging Face token not found, cannot query Granite.")
        return None

    prompt = f"""
Instruction: You are a medical data extraction tool. Analyze the following prescription note and extract all drug names and their corresponding dosages.
Your response MUST be a valid JSON list of objects, where each object has a "name" and a "dosage" key. If a dosage is not mentioned, set the value to null.

Prescription Note: "{text}"

JSON Response:
"""
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 256, "temperature": 0.1, "return_full_text": False}}

    try:
        response = requests.post(GRANITE_API_URL, headers=HF_HEADERS, json=payload, timeout=45)
        if response.status_code == 200:
            generated_text = response.json()[0]['generated_text'].strip()
            # Search for the JSON block within the response
            match = re.search(r'\[.*\]', generated_text, re.DOTALL)
            if match:
                json_string = match.group(0)
                try:
                    print("Successfully extracted data using IBM Granite.")
                    return json.loads(json_string)
                except json.JSONDecodeError:
                    print(f"Granite returned a JSON-like string but it was invalid: {json_string}")
                    return None
        print(f"Granite API returned an error: {response.status_code} - {response.text}")
        return None # Signal failure
    except requests.exceptions.RequestException as e:
        print(f"A network error occurred while contacting Granite: {e}")
        return None # Signal failure

def _query_google_for_extraction(text: str) -> list:
    """Extracts data using the Google Gemini API as a reliable backup."""
    if not GOOGLE_API_KEY:
        print("Google API Key not found. Cannot fall back.")
        return []

    prompt = f"""
You are a highly precise data extraction tool. Analyze the following medical note.
Extract all drug names and their dosages into a valid JSON list of objects.
Each object must have two keys: "name" and "dosage". If a dosage is not explicitly mentioned for a drug, set its value to null.
Do not provide any explanation or introductory text. Your output must be only the JSON list.

Medical Note: "{text}"
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GOOGLE_API_URL, headers=GOOGLE_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Google's Gemini sometimes wraps the JSON in markdown backticks, so we clean it up
        response_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        
        print("Successfully extracted data using Google Gemini fallback.")
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"An error occurred while falling back to Google Gemini: {e}")
        return []

def extract_drug_info(text: str) -> list:
    """
    Main function for extraction. First tries IBM Granite, falls back to Google Gemini on failure.
    """
    print("Attempting to extract data using IBM Granite...")
    granite_response = _query_granite_for_extraction(text)
    
    if granite_response is not None:
        return granite_response
    
    print("IBM Granite failed or is unavailable. Falling back to Google Gemini for extraction.")
    return _query_google_for_extraction(text)

