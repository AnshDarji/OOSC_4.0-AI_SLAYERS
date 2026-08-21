import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
keys_str = os.getenv("GEMINI_API_KEYS", "")
key = [k.strip() for k in keys_str.split(",") if k.strip()][0]

client = genai.Client(api_key=key)

prompt = "Hello"
models = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-flash-lite-latest", "gemini-2.0-flash-lite"]

for m in models:
    try:
        r = client.models.generate_content(model=m, contents=prompt)
        print(f"{m} SUCCESS: {r.text[:50]}")
    except Exception as e:
        print(f"{m} ERROR: {e}")
