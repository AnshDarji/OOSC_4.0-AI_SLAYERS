import re
import os

filepath = r"app/ai/prompt_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

defense_instructions = """
SECONDARY RELEVANCE DEFENSE:
- Do not treat a source as applicable merely because it contains a matching term (e.g., 'local authority', 'police').
- Determine whether the source actually governs or materially informs the legal issue.
- If retrieved sources are irrelevant, do not construct an answer from them. State clearly that the available retrieval does not contain sufficient directly applicable authority, and identify what type of authority is missing.
- Do NOT hallucinate the missing law, authorities, sections, or escalation hierarchies to make the answer look complete.
"""

code = code.replace("3. Never invent or hallucinate law.", "3. Never invent or hallucinate law." + defense_instructions)

code = code.replace("3. NEVER hallucinate laws, sections, cases, holdings, remedies, authorities, procedural facts, deadlines, or fees.", "3. NEVER hallucinate laws, sections, cases, holdings, remedies, authorities, procedural facts, deadlines, or fees." + defense_instructions)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Prompts patched successfully.")
