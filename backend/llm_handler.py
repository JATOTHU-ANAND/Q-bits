# llm_handler.py
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# --- Load BOTH API Keys ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Define BOTH Service Endpoints ---
HF_API_URL = "https://api-inference.huggingface.co/models/BioMistral/BioMistral-7B"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

GOOGLE_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
GOOGLE_HEADERS = {"Content-Type": "application/json"}


def _query_huggingface(prompt: str) -> str | None:
    """Attempts to query the Hugging Face API. Returns None on failure."""
    if not HF_API_TOKEN:
        print("Hugging Face token not found, skipping.")
        return None
    
    payload = {
        "inputs": f"[INST] {prompt} [/INST]",
        "parameters": {"max_new_tokens": 250, "temperature": 0.5, "return_full_text": False}
    }
    try:
        response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload, timeout=45)
        if response.status_code == 200:
            print("Successfully received response from Hugging Face.")
            return response.json()[0]['generated_text'].strip()
        else:
            print(f"Hugging Face API returned an error: {response.status_code} - {response.text}")
            return None # Signal failure
    except requests.exceptions.RequestException as e:
        print(f"A network error occurred while contacting Hugging Face: {e}")
        return None # Signal failure

def _query_google_ai(prompt: str) -> str:
    """Queries the Google Gemini API as a reliable backup."""
    if not GOOGLE_API_KEY:
        return "ERROR: Google API Key is missing. Please configure your .env file."

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(GOOGLE_API_URL, headers=GOOGLE_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        return "Received an unexpected response from Google AI."
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while contacting Google AI: {e}")
        return "An error occurred while communicating with the backup AI model."

def query_llm_with_fallback(prompt: str) -> str:
    """
    Main function to query LLMs. First tries Hugging Face, falls back to Google AI on failure.
    """
    print("Attempting to use Hugging Face API...")
    hf_response = _query_huggingface(prompt)
    
    if hf_response:
        return hf_response
    
    print("Hugging Face API failed or is unavailable. Falling back to Google Gemini API.")
    return _query_google_ai(prompt)


# --- The functions called by main.py remain the same ---
# They now use the new intelligent fallback system automatically.

def analyze_dosage_with_llm(age: int, drug: str, dosage: str) -> str:
    """Asks the LLM to analyze if a dosage is appropriate for a given age."""
    prompt = f"""
    You are a clinical AI assistant. Analyze if the dosage '{dosage}' for the drug '{drug}' is generally appropriate for a patient who is {age} years old.
    Provide a concise conclusion, a brief explanation based on known medical guidelines, and a clear disclaimer that this is not medical advice.
    """
    return query_llm_with_fallback(prompt)

def suggest_alternatives_with_llm(problem_drug: str, interacting_drug: str) -> str:
    """Asks the LLM to suggest safer alternatives."""
    prompt = f"""
    You are a clinical AI assistant. A patient is taking '{interacting_drug}' which has a known harmful interaction with '{problem_drug}'.
    Suggest one common, safer alternative medication for '{problem_drug}' that belongs to a similar drug class but with a lower interaction risk. Explain your reasoning briefly.
    """
    return query_llm_with_fallback(prompt)