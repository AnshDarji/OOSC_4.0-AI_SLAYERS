import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database.database import SessionLocal
from app.services.kanoon_service import kanoon_service
from app.schemas.kanoon import KanoonQueryRequest
from app.ai.prompt_builder import prompt_builder
from fastapi import BackgroundTasks

class DummyBackgroundTasks:
    def add_task(self, *args, **kwargs):
        pass

db = SessionLocal()
bg = DummyBackgroundTasks()

queries = [
    "I filed an RTI 60 days ago to know my property mutation status but got no reply.",
    "My Amazon phone arrived broken and the seller refuses to give a refund.",
    "My landlord locked me out because I missed one month's rent. I live in Mumbai."
]

sizes = [
    ("1500", 6000),
    ("1000", 4000),
    ("800", 3200),
    ("600", 2400),
    ("400", 1600)
]

print("--- EVIDENCE COMPRESSION BENCHMARK ---")

for q in queries:
    print(f"\n======================================")
    print(f"QUERY: {q}")
    print(f"======================================")
    
    for size_name, max_chars in sizes:
        # Monkey-patch the compressor limit for this run
        original_compress = prompt_builder.compress_evidence
        def patched_compress(question, chunks, mc=max_chars):
            return original_compress(question, chunks, max_chars=mc)
        prompt_builder.compress_evidence = patched_compress
        
        req = KanoonQueryRequest(question=q, conversation_id=f"test_{size_name}")
        
        start_time = time.time()
        ttft = None
        full_text = ""
        
        try:
            stream = kanoon_service.query_stream(req, "test_user", db, bg)
            # Drain stream
            for event in stream:
                if event.startswith("data: "):
                    try:
                        data = json.loads(event[6:])
                        if data.get("type") == "chunk":
                            if ttft is None:
                                ttft = time.time() - start_time
                            full_text += data.get("data", "")
                    except:
                        pass
            total_time = time.time() - start_time
            out_tokens = len(full_text) // 4
            print(f"[{size_name} tokens]: TTFT: {ttft*1000 if ttft else 0:.2f}ms | Total: {total_time*1000:.2f}ms | Output Tokens: {out_tokens}")
            print(f"Sample: {full_text[:100]}...\n")
        except Exception as e:
            print(f"[{size_name} tokens]: ERROR: {e}\n")
            
        # Restore
        prompt_builder.compress_evidence = original_compress
        time.sleep(1) # Quota protection
        
