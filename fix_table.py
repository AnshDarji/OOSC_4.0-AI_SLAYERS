import sys
import re

new_table = """## Performance Snapshot

| Metric | Value | Measurement / Basis |
|--------|------:|---------------------|
| Corpus Size | 93 Bare Acts | Ingested statutory documents |
| Judgments | 4,369 | Acquired and prepared for ingestion |
| Retrieval Strategy | Metadata-aware Hybrid RAG | Production implementation |
| Top-k Retrieved Chunks | 8 | Configured threshold for retrieval |
| Prompt Context | ~4.5k tokens | Internal benchmark average |
| Retrieval Latency | 10 ms | Average over benchmark runs |
| Average Response Time | ~2.8 s | Average Pure Model Latency |
| Irrelevant Retrieval Reduction | ~90% | Internal benchmark vs naïve vector-only retrieval |
| Estimated Token Reduction | ~35–60% | Compared against naïve top-k retrieval without metadata filtering |
| Estimated API Cost Savings | Proportional | Based on reduced prompt context compared to baseline RAG |

"""

try:
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the bounds of the Performance Snapshot section
    pattern = re.compile(r'## Performance Snapshot.*?---', re.DOTALL)
    
    if pattern.search(content):
        content = pattern.sub(new_table + "---", content)
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Table fixed successfully.")
    else:
        print("Could not find the Performance Snapshot section.")
except Exception as e:
    print(f"Error: {e}")
