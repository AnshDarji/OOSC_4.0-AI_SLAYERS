import json
import re
import os
import sys

# Ensure vector store path is available
sys.path.append(os.getcwd())
from app.knowledge.vector_store import vector_store

data = vector_store.collection.get(include=['metadatas'])
from collections import Counter
c = Counter([m.get('source_name') for m in data['metadatas'] if m])

# Define categories
acts = []
cases = []
rules = []
other = []
duplicates = []

def parse_act_name(raw_name):
    name = raw_name.replace('_', ' ')
    year_match = re.search(r'\b(18|19|20)\d{2}\b', name)
    year = year_match.group(0) if year_match else 'Not specified in corpus'
    clean_name = re.sub(r'\b(18|19|20)\d{2}\b', '', name).strip().title()
    
    # Capitalization fixes
    clean_name = clean_name.replace(" Of ", " of ").replace(" And ", " and ").replace(" For ", " for ")
    clean_name = clean_name.replace(" To ", " to ").replace(" On ", " on ").replace(" The ", " the ")
    
    return clean_name, year

for raw, count in c.items():
    if 'judgment' in raw.lower():
        clean_name = raw.replace('judgment_', '').replace('_', ' ').title()
        cases.append({
            "raw": raw,
            "name": clean_name + " Case",
            "year": "Not specified in corpus",
            "type": "Judgment",
            "jurisdiction": "Supreme Court of India (presumed)",
            "chunks": count
        })
    elif 'india france' in raw.lower() or 'india-france' in raw.lower():
        rules.append({
            "raw": raw,
            "name": raw,
            "year": "Not specified in corpus",
            "type": "Treaty / Convention",
            "jurisdiction": "International",
            "chunks": count
        })
    elif 'mock' in raw.lower():
        other.append({
            "raw": raw,
            "name": "Mock Act",
            "year": "Not specified in corpus",
            "type": "Mock Data",
            "jurisdiction": "Not specified in corpus",
            "chunks": count
        })
    else:
        clean_name, year = parse_act_name(raw)
        
        type_str = "Act"
        if "Code" in clean_name or "Sanhita" in clean_name:
            type_str = "Code"
        elif "Constitution" in clean_name:
            type_str = "Constitution"
            
        acts.append({
            "raw": raw,
            "name": clean_name,
            "year": year,
            "type": type_str,
            "jurisdiction": "Central", # By default, most are central in this dataset except specific state ones
            "chunks": count
        })

# Identify Duplicates (Same underlying name)
act_names = {}
for a in acts:
    norm = a['name'].lower().replace(' ', '')
    if norm not in act_names:
        act_names[norm] = []
    act_names[norm].append(a)

for norm, arr in act_names.items():
    if len(arr) > 1:
        for a in arr:
            duplicates.append(a['raw'])

# State specific overrides
for a in acts:
    if "Maharashtra" in a["name"]:
        a["jurisdiction"] = "Maharashtra"
    if "Delhi" in a["name"]:
        a["jurisdiction"] = "Delhi"

# Sort
acts = sorted(acts, key=lambda x: x['name'])
cases = sorted(cases, key=lambda x: x['name'])
rules = sorted(rules, key=lambda x: x['name'])

with open(r'C:\Users\ANSH DARJI\.gemini\antigravity\brain\d3334e88-e108-4152-be67-6548a3927f99\legal_corpus_inventory.md', 'w', encoding='utf-8') as f:
    f.write("### 1. Executive Corpus Statistics\n\n")
    f.write(f"**Total unique Acts/Codes:** {len(act_names.keys())}\n")
    f.write(f"**Total unique cases/judgments:** {len(cases)}\n")
    f.write(f"**Total unique rules/regulations:** {len(rules)}\n")
    f.write(f"**Total other legal documents:** {len(other)}\n")
    f.write(f"**Total unique legal sources (deduplicated):** {len(act_names.keys()) + len(cases) + len(rules) + len(other)}\n\n")

    f.write("### 2. Complete Acts & Codes Inventory\n\n")
    for a in acts:
        dup_str = " (Partially represented / Duplicate version)" if a['raw'] in duplicates and a['chunks'] < 5 else ""
        f.write(f"* **{a['name']}**, {a['year']} — Type: {a['type']} — Jurisdiction: {a['jurisdiction']} ({a['chunks']} chunks){dup_str}\n")

    f.write("\n### 3. Complete Case/Judgment Inventory\n\n")
    for c in cases:
        f.write(f"* **{c['name']}** — Court: {c['jurisdiction']} — Citation: Not specified in corpus — ({c['chunks']} chunks)\n")

    f.write("\n### 4. Complete Rules/Regulations/Notifications/Treaties Inventory\n\n")
    for r in rules:
        f.write(f"* **{r['name']}** — Type: {r['type']} — ({r['chunks']} chunks)\n")

    f.write("\n### 5. Other Legal Sources\n\n")
    for o in other:
        f.write(f"* **{o['name']}** — Type: {o['type']} — ({o['chunks']} chunks)\n")

    f.write("\n### 6. Duplicates / Versions / Amendments\n\n")
    f.write("The following document pairs were identified as duplicates or different versions/chunks of the same underlying source:\n\n")
    for norm, arr in act_names.items():
        if len(arr) > 1:
            names = [f"`{x['raw']}` ({x['chunks']} chunks)" for x in arr]
            f.write(f"* **{arr[0]['name']}**: " + " vs. ".join(names) + "\n")
            
    f.write("\nAlso identified treaty duplicates:\n")
    f.write("* `India France Sample.pdf` vs. `India-France-100726.pdf` (both have 36 chunks).\n")

    f.write("\n### 7. Master List of Every Unique Legal Source\n\n")
    f.write("| # | Category | Exact Name | Year | Jurisdiction | Court/Authority | Citation/Identifier | Source/Document |\n")
    f.write("| - | -------- | ---------- | ---- | ------------ | --------------- | ------------------- | --------------- |\n")

    counter = 1
    for arr in act_names.values():
        a = arr[0] # Pick the primary one
        f.write(f"| {counter} | {a['type']} | {a['name']} | {a['year']} | {a['jurisdiction']} | Not specified in corpus | {a['raw']} | {a['raw']} |\n")
        counter += 1

    for c in cases:
        f.write(f"| {counter} | {c['type']} | {c['name']} | {c['year']} | Not specified in corpus | {c['jurisdiction']} | Not specified in corpus | {c['raw']} |\n")
        counter += 1

    for r in rules:
        f.write(f"| {counter} | {r['type']} | {r['name']} | {r['year']} | {r['jurisdiction']} | Not specified in corpus | Not specified in corpus | {r['raw']} |\n")
        counter += 1

    for o in other:
        f.write(f"| {counter} | {o['type']} | {o['name']} | {o['year']} | {o['jurisdiction']} | Not specified in corpus | Not specified in corpus | {o['raw']} |\n")
        counter += 1

    f.write("\n### 8. Completeness and Metadata Gaps\n\n")
    f.write("* **Case Citations/Numbers:** Completely missing from the database schema. Only raw names (`judgment_kesavananda_bharati`) are present.\n")
    f.write("* **Chunk Representation:** Several Acts (e.g., `CPC_1908`, `BSA_2023`, `Indian_Contract_Act`) have only 1-2 chunks in the database, representing a severely truncated or partially ingested version compared to their primary fully ingested counterparts (e.g., `CODE_OF_CIVIL_PROCEDURE_1908` with 480 chunks).\n")
    f.write("* **Treaty Origins:** The India-France document does not specify exact dates or notification numbers.\n")


