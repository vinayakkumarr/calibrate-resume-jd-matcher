import os
import sys

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from google import genai
from google.genai import types

def verify_gate_zero():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[FAIL] GEMINI_API_KEY is not set in .env.")
        sys.exit(1)

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    print(f"Checking Gemini API Free-Tier structured schema capabilities using model: {model}...")
    client = genai.Client(api_key=api_key)

    schema = {
        "type": "OBJECT",
        "properties": {
            "status": {"type": "STRING"},
            "test_score": {"type": "NUMBER"}
        },
        "required": ["status", "test_score"]
    }

    try:
        response = client.models.generate_content(
            model=model,
            contents="Output status 'verified' and test_score 100.",
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        print("Raw response:", response.text)
        print("[SUCCESS] Gate 0 Passed! Gemini Free Tier supports response_schema.")
    except Exception as e:
        print(f"[FAIL] Gate 0: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    verify_gate_zero()
