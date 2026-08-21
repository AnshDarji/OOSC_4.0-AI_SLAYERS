import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
keys_str = os.getenv("GEMINI_API_KEYS", "")
key = [k.strip() for k in keys_str.split(",") if k.strip()][0]

client = genai.Client(api_key=key)

for m in client.models.list_models():
    if "flash" in m.name:
        print(m.name)
