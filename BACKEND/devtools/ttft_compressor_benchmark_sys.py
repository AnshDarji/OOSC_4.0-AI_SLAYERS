import time
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
keys_str = os.getenv("GEMINI_API_KEYS", "")
key = [k.strip() for k in keys_str.split(",") if k.strip()][0]
client = genai.Client(api_key=key)

system_instruction = """You are NYAAY AI, a fast Civic & Legal responder.
Your goal is to give a citizen an actionable path to resolution using ONLY retrieved authorities.

CORE PRINCIPLES:
1. Move from Information to Action.
2. NEVER hallucinate procedural facts, deadlines, fees, or portals.
3. Be jurisdiction-aware based on the context.
4. Use [X] inline citations for claims.

STRUCTURE YOUR RESPONSE EXACTLY AS FOLLOWS. KEEP IT ULTRA-CONCISE.

1. Right Violated / Applicable Right:
State the user's specific right that was violated based on the facts (Maximum 1 sentence). Cite relevant Act/Section using [X].

2. Evidence:
Provide a maximum of 3 bullet points listing documents the user must gather.

3. Authority:
Name the specific authority to approach (Name only). DO NOT invent an authority (e.g. 'Local District Court') if not explicitly stated in context. If the authority is not explicitly in the context, output exactly: "Refer to the authority specified in the cited source."

4. Action:
Provide a maximum of 3 bullet points listing chronological steps to take.

5. Document Type:
Name only the recommended document template to use (e.g., RTI Application, Legal Notice).

DO NOT generate long explanations, act descriptions, or repeat source metadata.
"""

def generate_context(target_tokens):
    base_text = "The tenant is protected under the Rent Control Act against unlawful eviction. The landlord must provide a written notice of at least 30 days before initiating eviction proceedings. Failure to do so renders the lockout illegal, and the tenant may approach the Rent Tribunal for immediate restoration of possession. "
    base_tokens = len(base_text) // 4
    repeats = max(1, target_tokens // base_tokens)
    return (base_text * repeats)[:target_tokens * 4]

sizes = [1500, 1000, 800, 600, 400]
query = "My landlord locked me out because I missed one month's rent. I live in Mumbai."

print("--- TRUE TTFT ISOLATION BENCHMARK (WITH SYSTEM PROMPT) ---")
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
                system_instruction=system_instruction
            )
        )
        
        ttft = None
        for chunk in response_stream:
            if ttft is None:
                ttft = time.time() - t_start
                first_token = chunk.text
        
        t_total = time.time() - t_start
        print(f"Context Tokens: ~{size} | True TTFT: {ttft*1000:.2f}ms | Total: {t_total*1000:.2f}ms")
    except Exception as e:
        print(f"Size {size} failed: {e}")
        
    time.sleep(1)
