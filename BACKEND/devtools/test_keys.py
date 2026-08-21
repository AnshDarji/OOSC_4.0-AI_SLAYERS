import time
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("GEMINI_API_KEYS", "")
keys = [k.strip() for k in keys_str.split(",") if k.strip()]

prompt = "Hello, just a 5 word response please."

for i, key in enumerate(keys):
    try:
        client = genai.Client(api_key=key)
        print(f"\n--- Testing Key {i+1} ---")
        start_time = time.time()
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        ttft = None
        for chunk in response_stream:
            if ttft is None:
                ttft = time.time() - start_time
        total_time = time.time() - start_time
        print(f"Success! TTFT: {ttft*1000:.2f}ms, Total: {total_time*1000:.2f}ms")
    except Exception as e:
        print(f"Error: {e}")
