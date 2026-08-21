import os

filepath = r"c:\Users\ANSH DARJI\Documents\NYAAY AI\BACKEND\app\ai\orchestrator.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# We want to replace the `trigger_pipeline_stream` and `_generate_with_fallback` methods
# Let's find the start of `def trigger_pipeline_stream`
start_idx = code.find("    def trigger_pipeline_stream")
end_idx = code.find("rag_orchestrator = RAGOrchestrator()")

new_methods = """    def trigger_pipeline_stream(self, question: str, filters: Dict[str, Any] = None, history: List[Dict[str, Any]] = None, task_type: str = "QA"):
        import time
        import json
        import asyncio
        from app.core.config import settings
        
        overall_start = time.time()
        
        yield f"data: {json.dumps({'type': 'status', 'data': 'Analyzing intent...'})}\\n\\n"
        
        if not guardrails.validate_input(question):
            yield f"data: {json.dumps({'type': 'error', 'data': 'Your question violates safety or length policies.'})}\\n\\n"
            return

        search_query = self._rewrite_query(question, history)

        yield f"data: {json.dumps({'type': 'status', 'data': 'Searching legal corpus...'})}\\n\\n"
        
        emb_start = time.time()
        try:
            query_embedding = embedding_service.embed_query(search_query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Internal error while processing your question.'})}\\n\\n"
            return
        emb_latency = round(time.time() - emb_start, 2)

        if not query_embedding:
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to process question text.'})}\\n\\n"
            return
            
        from app.ai.domain_classifier import domain_classifier
        domain_predictions = domain_classifier.predict_domain(search_query)
        predicted_domains = domain_predictions.get("domains", {})
        doc_type_priority = domain_predictions.get("document_type_priority", "any")

        retrieval_start = time.time()
        try:
            chunks = hybrid_retriever.search(
                query=search_query, 
                query_embedding=query_embedding, 
                n_results=12, # Kept at 12 to preserve accuracy
                where=filters,
                predicted_domains=predicted_domains,
                document_type_priority=doc_type_priority
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to retrieve context.'})}\\n\\n"
            return
        retrieval_latency = round(time.time() - retrieval_start, 2)
        
        # EXTRACT DETERMINISTIC METADATA EARLY
        extracted_authorities = set()
        extracted_docs = set()
        for c in chunks[:3]:
            m = c.get("metadata", {})
            if "authority" in m:
                extracted_authorities.add(m["authority"])
            if "document_type" in m:
                extracted_docs.add(m["document_type"])
                
        # Emit metadata early
        metadata_payload = {
            "authorities": list(extracted_authorities) if extracted_authorities else ["Refer to cited procedure"],
            "documents": list(extracted_docs)
        }
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata_payload})}\\n\\n"

        pc_start = time.time()
        system_instruction, user_prompt = prompt_builder.construct_prompt(question, chunks, history, task_type=task_type)
        pc_latency = round(time.time() - pc_start, 2)
        
        yield f"data: {json.dumps({'type': 'status', 'data': 'Generating response...'})}\\n\\n"

        gen_start = time.time()
        full_text = ""
        ttft = None
        
        try:
            model_name = getattr(settings, "CIVIC_MODEL", "gemini-2.5-flash")
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=300,
            )
            # Disable thinking if possible
            try:
                config.thinking_config = types.ThinkingConfig(disabled=True)
            except Exception:
                pass

            import threading
            import queue
            
            q = queue.Queue()
            
            def run_gen():
                try:
                    temp_client = genai.Client(api_key=key_rotator.get())
                    response_stream = temp_client.models.generate_content_stream(
                        model=model_name,
                        contents=user_prompt,
                        config=config,
                    )
                    for chunk in response_stream:
                        q.put(("chunk", chunk.text))
                    q.put(("done", None))
                except Exception as e:
                    q.put(("error", e))
                    
            t = threading.Thread(target=run_gen)
            t.start()
            
            deadline = time.time() + 6.5
            while True:
                time_left = deadline - time.time()
                if time_left <= 0:
                    yield f"data: {json.dumps({'type': 'error', 'data': '\\n\\n[Generation timed out to meet 7s SLA]'})}\\n\\n"
                    break
                    
                try:
                    msg_type, data = q.get(timeout=min(0.5, time_left))
                    if msg_type == "chunk":
                        if ttft is None:
                            ttft = time.time() - gen_start
                        if data:
                            full_text += data
                            yield f"data: {json.dumps({'type': 'chunk', 'data': data})}\\n\\n"
                    elif msg_type == "done":
                        break
                    elif msg_type == "error":
                        error_str = str(data)
                        logger.warning(f"Streaming error: {error_str}")
                        if "GenerateRequestsPerDayPerProject" in error_str:
                            key_rotator.remove_key(temp_client.api_key)
                        yield f"data: {json.dumps({'type': 'error', 'data': 'Generation interrupted due to quota limit.'})}\\n\\n"
                        break
                except queue.Empty:
                    continue
                    
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Generation failed.'})}\\n\\n"

        gen_total_latency = time.time() - gen_start
        total_latency = round(time.time() - overall_start, 2)
        
        metrics = {
            "embedding_time": emb_latency,
            "retrieval_time": retrieval_latency,
            "prompt_construction_time": pc_latency,
            "ttft": round(ttft, 2) if ttft else 0,
            "model_processing_time": round(gen_total_latency, 2),
            "output_tokens": len(full_text) // 4,
            "total_latency": total_latency
        }
        
        used_citations = set(re.findall(r'\[(\d+)\]', full_text))
        citations = []
        for i, chunk in enumerate(chunks):
            marker_num = str(i + 1)
            if marker_num in used_citations or not used_citations:
                meta = chunk.get("metadata", {})
                citations.append({
                    "marker": f"[{marker_num}]",
                    "text_snippet": chunk["document"][:150] + "...",
                    "source_name": meta.get("source_name", "Unknown"),
                    "article_or_section": meta.get("section", meta.get("article", "Unknown")),
                    "legal_domain": meta.get("legal_domain", ""),
                    "metadata": meta
                })

        yield f"data: {json.dumps({'type': 'complete', 'citations': citations, 'metrics': metrics})}\\n\\n"

    def _generate_with_fallback(self, system_instruction: str, user_prompt: str) -> tuple[str, float]:
        import time
        from app.core.config import settings
        max_retries = 2
        total_sleep_time = 0.0
        
        model_name = getattr(settings, "CIVIC_MODEL", "gemini-2.5-flash")
        
        for attempt in range(max_retries):
            try:
                temp_client = genai.Client(api_key=key_rotator.get())
                response = temp_client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    ),
                )
                return response.text.strip(), total_sleep_time
            except Exception as e:
                error_str = str(e)
                logger.warning(f"RAG Generation failed on attempt {attempt+1}: {error_str}")
                
                if "GenerateRequestsPerDayPerProject" in error_str:
                    logger.warning("Daily quota exhausted, dropping key.")
                    key_rotator.remove_key(temp_client.api_key)
                    continue
                elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    sleep_time = 0.5
                    time.sleep(sleep_time)
                    total_sleep_time += sleep_time
                continue
                
        return None, total_sleep_time

    def _fallback_response(self, message: str) -> Dict[str, Any]:
        return {
            "answer": message,
            "citations": [],
            "confidence": {
                "level": "Insufficient",
                "reason": message,
            },
            "metrics": {}
        }

"""

new_code = code[:start_idx] + new_methods + code[end_idx:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_code)
print("orchestrator.py patched successfully")
