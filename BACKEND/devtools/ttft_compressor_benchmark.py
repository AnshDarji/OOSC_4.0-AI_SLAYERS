import time
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
keys_str = os.getenv("GEMINI_API_KEYS", "")
# Use a specific key, or just let it grab the first
key = [k.strip() for k in keys_str.split(",") if k.strip()][0]
client = genai.Client(api_key=key)

# Generate dummy context to simulate token loads accurately
def generate_context(target_tokens):
    # roughly 4 chars per token.
    # We'll repeat a standard legal sounding paragraph.
    base_text = "The tenant is protected under the Rent Control Act against unlawful eviction. The landlord must provide a written notice of at least 30 days before initiating eviction proceedings. Failure to do so renders the lockout illegal, and the tenant may approach the Rent Tribunal for immediate restoration of possession. "
    base_tokens = len(base_text) // 4
    repeats = max(1, target_tokens // base_tokens)
    return (base_text * repeats)[:target_tokens * 4]

sizes = [1500, 1000, 800, 600, 400]
query = "My landlord locked me out because I missed one month's rent. I live in Mumbai."

print("--- TRUE TTFT ISOLATION BENCHMARK ---")
for size in sizes:
    context = generate_context(size)
    prompt = f"CONTEXT:\n{context}\n\nUSER QUERY:\n{query}\n\nRespond concisely."
    
    t_start = time.time()
    try:
        response_stream = client.models.generate_content_stream(
            model="gemini-flash-lite-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=300,
            )
        )
        
        ttft = None
        t_net_start = time.time()
        
        for chunk in response_stream:
            if ttft is None:
                ttft = time.time() - t_net_start
                first_token = chunk.text
        
        t_total = time.time() - t_start
        print(f"Context Tokens: ~{size} | True TTFT: {ttft*1000:.2f}ms | Total: {t_total*1000:.2f}ms")
    except Exception as e:
        print(f"Size {size} failed: {e}")
        
    time.sleep(1) # short cooldown to protect quota
