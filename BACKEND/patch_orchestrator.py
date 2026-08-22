import re
import os

filepath = r"app/ai/orchestrator.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# Replace _rewrite_query with _analyze_and_expand_query
new_query_func = '''    def _analyze_and_expand_query(self, question: str, history: List[Dict[str, Any]]) -> str:
        sys_prompt = """You are a legal query analyzer. Extract the core legal issue from the user's query and expand it into a comprehensive search query for a legal vector database.
Include relevant legal concepts, synonyms, and possible statutory frameworks (e.g., if it's about garbage collection, include solid waste management, municipal sanitation duties, public health, administrative inaction, nuisance, etc.).
DO NOT just repeat the user's text. Extract the true legal problem.
Output ONLY the expanded search query, nothing else."""
        
        history_text = "Conversation History:\\n"
        if history:
            for msg in history[-4:]:
                text_content = msg.get('content') or (msg.get('parts', [{}])[0].get('text', ''))
                history_text += f"{msg['role']}: {text_content}\\n"
        else:
            history_text = "No history."
            
        user_prompt = f"{history_text}\\nUser Query: {question}\\nExpanded Legal Search Query:"
        
        try:
            temp_client = genai.Client(api_key=key_rotator.get())
            res = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=sys_prompt)
            )
            expanded = res.text.strip()
            logger.info(f"Query expanded: '{question}' -> '{expanded}'")
            return expanded
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return question

    def _filter_relevant_chunks(self, question: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return chunks
            
        sys_prompt = """You are a Legal Relevance Filter for a RAG system.
Evaluate each retrieved legal document chunk against the user's query.
A chunk is DIRECTLY_APPLICABLE if it governs the legal issue.
A chunk is POTENTIALLY_RELEVANT if it materially informs the issue (e.g., case law discussing it, relevant statutes).
A chunk is IRRELEVANT if it merely mentions matching entities (e.g., 'local authority', 'police', 'goods') but does NOT govern the legal issue in the query.
Respond with a valid JSON array of objects, where each object has 'id' (the chunk index provided) and 'classification' (one of the 3 labels)."""

        user_prompt = f"User's Legal Query: {question}\\n\\n"
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            src = meta.get("source_name", "Unknown")
            user_prompt += f"--- Chunk ID: {i} | Source: {src} ---\\n{chunk['document'][:800]}\\n\\n"
            
        try:
            temp_client = genai.Client(api_key=key_rotator.get())
            res = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    response_mime_type="application/json"
                )
            )
            import json
            classifications = json.loads(res.text)
            
            valid_indices = set()
            for item in classifications:
                if item.get("classification") in ["DIRECTLY_APPLICABLE", "POTENTIALLY_RELEVANT"]:
                    valid_indices.add(item.get("id"))
                    
            filtered_chunks = [chunks[i] for i in range(len(chunks)) if i in valid_indices]
            logger.info(f"Filtered chunks from {len(chunks)} down to {len(filtered_chunks)}")
            return filtered_chunks
        except Exception as e:
            logger.warning(f"Relevance filtering failed: {e}")
            return chunks
'''

code = re.sub(r'    def _rewrite_query\(.*?(?=    def trigger_pipeline)', new_query_func, code, flags=re.DOTALL)

# Now replace calls to _rewrite_query with _analyze_and_expand_query
code = code.replace("search_query = self._rewrite_query(question, history)", "search_query = self._analyze_and_expand_query(question, history)")

# Now inject _filter_relevant_chunks after hybrid_retriever.search
patch_filter = '''            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._fallback_response("Failed to retrieve context.")
            
        # 3.5 LEGAL RELEVANCE GATE
        chunks = self._filter_relevant_chunks(question, chunks)
'''
code = code.replace('''            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._fallback_response("Failed to retrieve context.")''', patch_filter, 1) # Only for trigger_pipeline

patch_filter_stream = '''            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to retrieve context.'})}\\n\\n"
            return
            
        # 3.5 LEGAL RELEVANCE GATE
        chunks = self._filter_relevant_chunks(question, chunks)
'''
code = code.replace('''            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to retrieve context.'})}\\n\\n"
            return''', patch_filter_stream, 1) # Only for trigger_pipeline_stream

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Orchestrator patched successfully.")
