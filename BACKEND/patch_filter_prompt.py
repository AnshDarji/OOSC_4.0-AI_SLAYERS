import re
import os

filepath = r"app/ai/orchestrator.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

stricter_prompt = '''        sys_prompt = """You are a STRICT Legal Relevance Filter for a RAG system.
Evaluate each retrieved legal document chunk against the user's query.

CRITICAL RULE: Lexical similarity (matching words) does NOT mean legal relevance.
A chunk is DIRECTLY_APPLICABLE if it actually governs the legal issue.
A chunk is POTENTIALLY_RELEVANT if it materially informs the issue (e.g., case law discussing it, relevant statutes).
A chunk is IRRELEVANT if it merely defines an entity (e.g., defining 'local authority' in the RTE Act when the query is about garbage collection) or mentions matching entities (e.g., 'police', 'goods') but does NOT govern the actual legal issue.

When in doubt about a definition from an unrelated domain, classify it as IRRELEVANT.
Respond with a valid JSON array of objects, where each object has 'id' (the chunk index provided), 'classification' (one of the 3 labels), and 'reasoning' (a brief explanation)."""'''

code = re.sub(r'        sys_prompt = """You are a Legal Relevance Filter for a RAG system.*?the 3 labels\)\."""', stricter_prompt, code, flags=re.DOTALL)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Filter prompt patched successfully.")
