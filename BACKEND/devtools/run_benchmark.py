import requests
import json
import time

url = "http://127.0.0.1:8000/api/kanoon/query-stream"

queries = [
    "I filed an RTI 60 days ago to know my property mutation status but got no reply.",
    "My Amazon phone arrived broken and the seller refuses to give a refund.",
    "My landlord locked me out because I missed one month's rent. I live in Mumbai."
]

def benchmark():
    print("--- BENCHMARK STARTED ---")
    for q in queries:
        print(f"\nQuery: {q}")
        payload = {
            "conversation_id": "test_conv",
            "question": q,
            "domain_filters": {},
            "task_type": "CIVIC"
        }
        
        start_time = time.time()
        ttft = None
        full_text = ""
        
        try:
            with requests.post(url, json=payload, headers={"Authorization": "Bearer mock-token"}, stream=True, timeout=15) as r:
                for line in r.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith("data: "):
                            try:
                                data = json.loads(line_str[6:])
                                if data["type"] == "chunk" and ttft is None:
                                    ttft = time.time() - start_time
                                if data["type"] == "chunk":
                                    full_text += data["data"]
                                if data["type"] == "complete":
                                    metrics = data.get("metrics", {})
                                    metrics["total_latency"] = time.time() - start_time
                                    print(f"Metrics: {json.dumps(metrics, indent=2)}")
                                if data["type"] == "error":
                                    print(f"ERROR Event: {data['data']}")
                            except Exception as e:
                                pass
                                
        except Exception as e:
            print(f"Request failed: {e}")
            continue
            
        total_time = time.time() - start_time
        tokens = len(full_text) // 4
        print(f"TTFT: {ttft*1000 if ttft else 0:.2f}ms")
        print(f"Total Time: {total_time*1000:.2f}ms")
        print(f"Output Tokens (est): {tokens}")
        print(f"Text snippet: {full_text[:150]}...")
        print("-" * 40)

if __name__ == "__main__":
    benchmark()
