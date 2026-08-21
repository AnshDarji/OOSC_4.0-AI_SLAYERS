import time
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("GEMINI_API_KEYS", "")
keys = [k.strip() for k in keys_str.split(",") if k.strip()]

if not keys:
    print("No keys available.")
    exit(1)

client = genai.Client(api_key=keys[0])

def benchmark_model(model_name, prompt, max_tokens=None, thinking_disabled=False):
    config = types.GenerateContentConfig()
    if max_tokens:
        config.max_output_tokens = max_tokens
    
    # In some SDK versions, thinking_config is supported for newer models
    try:
        if thinking_disabled:
            # We will just pass an empty config or not use it if it throws an error
            config.thinking_config = types.ThinkingConfig(disabled=True)
    except Exception as e:
        pass
        
    start_time = time.time()
    try:
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=prompt,
            config=config
        )
        
        ttft = None
        output_tokens = 0
        full_text = ""
        
        for chunk in response_stream:
            if ttft is None:
                ttft = time.time() - start_time
            if chunk.text:
                full_text += chunk.text
                # Rough token estimation (chars / 4)
                output_tokens += len(chunk.text) / 4
                
        total_time = time.time() - start_time
        
        # Real token count if metadata exists
        try:
            # Not all stream responses have usage_metadata on the last chunk, but let's try
            pass 
        except:
            pass

        tokens_per_sec = output_tokens / (total_time - ttft) if (total_time - ttft) > 0 else 0
        
        return {
            "success": True,
            "ttft_ms": round(ttft * 1000, 2) if ttft else 0,
            "total_ms": round(total_time * 1000, 2),
            "est_tokens": round(output_tokens),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "text": full_text[:100] + "..."
        }
    except Exception as e:
        return {"success": False, "error": str(e), "total_ms": round((time.time() - start_time) * 1000, 2)}

prompt = """
You are a legal AI. Briefly explain the rights of a tenant in India when a landlord locks them out without notice. 
Provide 3 actionable steps.
"""

print(f"Testing with key starting with {keys[0][:10]}...")

models_to_test = [
    ("gemini-2.5-flash", False, None),
    ("gemini-2.5-flash", False, 200),
    ("gemini-1.5-flash", False, None), # Let's see if 1.5 is faster or available
]

for model, disable_thinking, max_tokens in models_to_test:
    print(f"\n--- Testing {model} | max_tokens={max_tokens} | disable_thinking={disable_thinking} ---")
    res = benchmark_model(model, prompt, max_tokens, disable_thinking)
    print(json.dumps(res, indent=2))
