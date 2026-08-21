import re

filepath = r"c:\Users\ANSH DARJI\Documents\NYAAY AI\BACKEND\app\ai\prompt_builder.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# We need to inject `compress_evidence` into PromptBuilder
compressor_code = """
    def compress_evidence(self, question: str, chunks: List[Dict[str, Any]], max_chars: int = 3200) -> List[Dict[str, Any]]:
        '''
        Deterministically compress evidence to ~800 tokens (3200 chars).
        1. Deduplicate by content overlap (Jaccard similarity).
        2. Rank by RRF score + exact phrase match boost.
        3. Keep full text for top chunks, truncate lower chunks if needed.
        '''
        import re
        
        # 1. Deduplicate
        unique_chunks = []
        seen_texts = set()
        
        def get_jaccard(s1, s2):
            w1 = set(re.findall(r'\w+', s1.lower()))
            w2 = set(re.findall(r'\w+', s2.lower()))
            if not w1 or not w2: return 0.0
            return len(w1.intersection(w2)) / len(w1.union(w2))
            
        for chunk in chunks:
            text = chunk.get("document", "")
            is_dup = False
            for seen in seen_texts:
                if get_jaccard(text, seen) > 0.8:  # 80% word overlap is a duplicate
                    is_dup = True
                    break
            if not is_dup:
                unique_chunks.append(chunk)
                seen_texts.add(text)
                
        # 2. Score & Rank
        q_words = set(re.findall(r'\w+', question.lower()))
        
        scored_chunks = []
        for i, chunk in enumerate(unique_chunks):
            # Base score is RRF position (since they arrive sorted)
            # Higher is better: 1/(i+1)
            base_score = 1.0 / (i + 1)
            
            text = chunk.get("document", "")
            t_words = set(re.findall(r'\w+', text.lower()))
            
            # Query overlap boost
            overlap = len(q_words.intersection(t_words))
            boost = overlap * 0.1
            
            final_score = base_score + boost
            scored_chunks.append((final_score, i, chunk))
            
        # Sort by final score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # 3. Budget allocation (Max 3200 chars ~ 800 tokens)
        compressed = []
        current_chars = 0
        
        # We need to preserve the original chunk ID (i+1) for citations!
        # So we return tuples of (original_index, chunk, truncated_text)
        
        # Find original indices
        original_indices = {id(c): idx for idx, c in enumerate(chunks)}
        
        for score, _, chunk in scored_chunks:
            orig_idx = original_indices[id(chunk)]
            text = chunk.get("document", "")
            
            if current_chars + len(text) <= max_chars:
                compressed.append((orig_idx, chunk, text))
                current_chars += len(text)
            else:
                # Truncate to fit remaining budget, min 100 chars to be useful
                rem = max_chars - current_chars
                if rem > 100:
                    compressed.append((orig_idx, chunk, text[:rem] + "..."))
                    current_chars += rem
                break
                
        # Re-sort by original index to keep citation numbering chronological
        compressed.sort(key=lambda x: x[0])
        return compressed
"""

# Now replace `construct_prompt` to use this compressor if task_type is CIVIC
old_construct = """    def construct_prompt(self, question: str, chunks: List[Dict[str, Any]], history: List[Dict[str, Any]] = None, task_type: str = "QA") -> tuple[str, str]:
        \"\"\"
        Constructs the final prompt.
        Returns (system_instruction, user_prompt)
        \"\"\"
        system_instruction = self.system_instructions.get(task_type, self.system_instructions["QA"])
        
        context_str = "CONTEXT CHUNKS:\\n\\n"
        for i, chunk in enumerate(chunks):
            # i+1 is the citation index
            metadata_str = []
            if "source_name" in chunk["metadata"]:
                metadata_str.append(f"Source: {chunk['metadata']['source_name']}")
            if "section" in chunk["metadata"]:
                metadata_str.append(f"Section: {chunk['metadata']['section']}")
            if "article" in chunk["metadata"]:
                metadata_str.append(f"Article: {chunk['metadata']['article']}")
                
            meta = ", ".join(metadata_str)
            context_str += f"--- Chunk [{i+1}] ({meta}) ---\\n{chunk['document']}\\n\\n"
"""

new_construct = """    def construct_prompt(self, question: str, chunks: List[Dict[str, Any]], history: List[Dict[str, Any]] = None, task_type: str = "QA") -> tuple[str, str]:
        \"\"\"
        Constructs the final prompt.
        Returns (system_instruction, user_prompt)
        \"\"\"
        system_instruction = self.system_instructions.get(task_type, self.system_instructions["QA"])
        
        context_str = "CONTEXT CHUNKS:\\n\\n"
        
        if task_type == "CIVIC":
            compressed = self.compress_evidence(question, chunks, max_chars=3200)
            for orig_idx, chunk, text in compressed:
                metadata_str = []
                if "source_name" in chunk["metadata"]:
                    metadata_str.append(f"Source: {chunk['metadata']['source_name']}")
                if "section" in chunk["metadata"]:
                    metadata_str.append(f"Section: {chunk['metadata']['section']}")
                
                meta = ", ".join(metadata_str)
                context_str += f"--- Chunk [{orig_idx+1}] ({meta}) ---\\n{text}\\n\\n"
        else:
            for i, chunk in enumerate(chunks):
                metadata_str = []
                if "source_name" in chunk["metadata"]:
                    metadata_str.append(f"Source: {chunk['metadata']['source_name']}")
                if "section" in chunk["metadata"]:
                    metadata_str.append(f"Section: {chunk['metadata']['section']}")
                    
                meta = ", ".join(metadata_str)
                context_str += f"--- Chunk [{i+1}] ({meta}) ---\\n{chunk['document']}\\n\\n"
"""

code = code.replace(old_construct, compressor_code + "\n" + new_construct)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)
print("Evidence Compressor injected successfully.")
