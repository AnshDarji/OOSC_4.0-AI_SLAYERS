from app.knowledge.hybrid_retriever import hybrid_retriever
from app.knowledge.embeddings import embedding_service
from app.core.config import settings
from app.core.key_rotator import key_rotator
import re
from typing import Dict, Any, List
from app.core.logger import logger
import concurrent.futures
from google import genai
from google.genai import types

from app.ai.guardrails import guardrails
from app.ai.prompt_builder import prompt_builder
from app.core.metrics import global_metrics
from app.ai.validator import calculate_retrieval_confidence, validate_response, extract_reasoning_confidence

class RAGOrchestrator:
    def __init__(self):
        # Base client for quick tasks, but we'll use rotator for heavy gen
        self.client = genai.Client(api_key=key_rotator.get())
        
    def _rewrite_query(self, question: str, history: List[Dict[str, Any]]) -> str:
        if not history:
            return question
            
        sys_prompt = "You are a query rewriter. Given a conversation history and a follow-up question, rewrite the follow-up question to be a standalone query that can be used for searching a vector database. Only output the rewritten query, nothing else."
        
        # Build prompt from history
        history_text = "Conversation History:\n"
        for msg in history[-4:]:
            text_content = msg.get('content') or (msg.get('parts', [{}])[0].get('text', ''))
            history_text += f"{msg['role']}: {text_content}\n"
        
        user_prompt = f"{history_text}\nFollow-up question: {question}\nRewritten standalone query:"
        
        try:
            temp_client = genai.Client(api_key=key_rotator.get())
            res = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=sys_prompt)
            )
            rewritten = res.text.strip()
            logger.info(f"Query rewritten: '{question}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return question

    def trigger_pipeline(self, question: str, filters: Dict[str, Any] = None, history: List[Dict[str, Any]] = None, task_type: str = "QA") -> Dict[str, Any]:
        """
        Executes the full RAG pipeline for a given question.
        """
        import time
        overall_start = time.time()
        
        # 1. Input Guardrails
        if not guardrails.validate_input(question):
            return self._fallback_response("Your question violates safety or length policies.")

        # 1.5 Conversational Query Rewriting
        search_query = self._rewrite_query(question, history)

        # 2. Embedding
        emb_start = time.time()
        try:
            query_embedding = embedding_service.embed_query(search_query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return self._fallback_response("Internal error while processing your question.")
        emb_latency = round(time.time() - emb_start, 2)

        if not query_embedding:
            return self._fallback_response("Failed to process question text.")
            
        # 2.5 Pre-Search Domain Classification
        from app.ai.domain_classifier import domain_classifier
        domain_predictions = domain_classifier.predict_domain(search_query)
        predicted_domains = domain_predictions.get("domains", {})
        doc_type_priority = domain_predictions.get("document_type_priority", "any")

        # 3. Hybrid Retrieval with Metadata Re-ranking
        retrieval_start = time.time()
        try:
            chunks = hybrid_retriever.search(
                query=search_query, 
                query_embedding=query_embedding, 
                n_results=10, 
                where=filters,
                predicted_domains=predicted_domains,
                document_type_priority=doc_type_priority
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._fallback_response("Failed to retrieve context.")
        retrieval_latency = round(time.time() - retrieval_start, 2)
        
        # Calculate Retrieval Confidence (Python Scoring)
        r_conf_score, r_conf_label, r_conf_reason, avg_score, max_score = calculate_retrieval_confidence(chunks)

        # 4. Prompt Construction
        pc_start = time.time()
        system_instruction, user_prompt = prompt_builder.construct_prompt(question, chunks, history, task_type=task_type)
        pc_latency = round(time.time() - pc_start, 2)
        
        gen_start = time.time()

        # 5. Generation (Single LLM Call)
        raw_answer, retry_sleep_time = self._generate_with_fallback(system_instruction, user_prompt)
        
        # 6. Deterministic Validation & Repair
        if raw_answer:
            is_valid, validated_answer = validate_response(raw_answer)
            if not is_valid:
                logger.warning(f"Validation failed: {validated_answer}. Regenerating once.")
                # Single Regeneration
                raw_answer, retry_sleep_time2 = self._generate_with_fallback(system_instruction, user_prompt)
                retry_sleep_time += retry_sleep_time2
                if raw_answer:
                    is_valid, validated_answer = validate_response(raw_answer)
                    raw_answer = validated_answer if is_valid else None
            else:
                raw_answer = validated_answer
                
        gen_total_latency = time.time() - gen_start
        model_processing_time = round(max(0, gen_total_latency - retry_sleep_time), 2)
        total_latency = round(time.time() - overall_start, 2)
        
        metrics = {
            "embedding_time": emb_latency,
            "retrieval_time": retrieval_latency,
            "prompt_construction_time": pc_latency,
            "model_processing_time": model_processing_time,
            "retry_delay_time": retry_sleep_time,
            "total_latency": total_latency
        }
        
        if not raw_answer:
            global_metrics.record_failure("llm_failures")
            return self._fallback_response("Failed to generate an answer. The AI service may be overloaded.")

        # 7. Extract Reasoning Confidence & Append Metadata
        rs_score, rs_label = extract_reasoning_confidence(raw_answer)
        
        used_citations = set(re.findall(r'\[(\d+)\]', raw_answer))
        auth_retrieved = len(chunks)
        auth_used = len(used_citations)
        
        statutes_used = 0
        sc_used = 0
        
        citations = []
        for i, chunk in enumerate(chunks):
            marker_num = str(i + 1)
            if marker_num in used_citations:
                meta = chunk.get("metadata", {})
                src_name = meta.get("source_name", "Unknown")
                domain = meta.get("legal_domain", "")
                
                if meta.get("document_type") == "statute" or "Act" in src_name or "Sanhita" in src_name:
                    statutes_used += 1
                elif meta.get("document_type") == "judgment" or meta.get("court") == "Supreme Court" or "Supreme Court" in src_name:
                    sc_used += 1
                    
                citations.append({
                    "marker": f"[{marker_num}]",
                    "text_snippet": chunk["document"][:150] + "...",
                    "source_name": src_name,
                    "article_or_section": meta.get("section", meta.get("article", "Unknown")),
                    "legal_domain": domain,
                    "retrieval_method": meta.get("retrieval_method", "unknown"),
                    "similarity_score": meta.get("rrf_score", 0.0),
                    "retrieval_rank": meta.get("retrieval_rank", i + 1),
                    "chunk_used_by_llm": True,
                    "metadata": meta
                })

        advanced_metadata = {
            "authorities_retrieved": auth_retrieved,
            "authorities_used": auth_used,
            "statutes_used": statutes_used,
            "sc_judgments_used": sc_used,
            "average_retrieval_score": round(avg_score, 4),
            "highest_retrieval_score": round(max_score, 4),
            "retrieval_time": retrieval_latency,
            "generation_time": model_processing_time,
            "corpus_coverage": "High" if auth_retrieved > 5 else "Low",
            "reasoning_confidence_score": rs_score
        }

        confidence_payload = {
            "level": r_conf_label if r_conf_label else "🟡 Moderate",
            "reason": r_conf_reason if r_conf_reason else "Derived from retrieved authorities."
        }

        return {
            "answer": raw_answer,
            "citations": citations,
            "confidence": confidence_payload,
            "advanced_metadata": advanced_metadata,
            "metrics": metrics
        }

    def trigger_pipeline_stream(self, question: str, filters: Dict[str, Any] = None, history: List[Dict[str, Any]] = None, task_type: str = "QA"):
        import time
        import json
        import asyncio
        from app.core.config import settings
        
        overall_start = time.time()
        
        yield f"data: {json.dumps({'type': 'status', 'data': 'Analyzing intent...'})}\n\n"
        
        if not guardrails.validate_input(question):
            yield f"data: {json.dumps({'type': 'error', 'data': 'Your question violates safety or length policies.'})}\n\n"
            return

        search_query = self._rewrite_query(question, history)

        yield f"data: {json.dumps({'type': 'status', 'data': 'Searching legal corpus...'})}\n\n"
        
        emb_start = time.time()
        try:
            query_embedding = embedding_service.embed_query(search_query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Internal error while processing your question.'})}\n\n"
            return
        emb_latency = round(time.time() - emb_start, 2)

        if not query_embedding:
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to process question text.'})}\n\n"
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
            yield f"data: {json.dumps({'type': 'error', 'data': 'Failed to retrieve context.'})}\n\n"
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
        yield f"data: {json.dumps({'type': 'metadata', 'data': metadata_payload})}\n\n"

        pc_start = time.time()
        system_instruction, user_prompt = prompt_builder.construct_prompt(question, chunks, history, task_type=task_type)
        pc_latency = round(time.time() - pc_start, 2)
        
        yield f"data: {json.dumps({'type': 'status', 'data': 'Generating response...'})}\n\n"

        gen_start = time.time()
        full_text = ""
        ttft = None
        
        try:
            model_name = getattr(settings, "CIVIC_MODEL", "gemini-flash-lite-latest")
            current_key = key_rotator.get()
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
                    temp_client = genai.Client(api_key=current_key)
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
                    yield f"data: {json.dumps({'type': 'error', 'data': '\n\n[Generation timed out to meet 7s SLA]'})}\n\n"
                    break
                    
                try:
                    msg_type, data = q.get(timeout=min(0.5, time_left))
                    if msg_type == "chunk":
                        if ttft is None:
                            ttft = time.time() - gen_start
                        if data:
                            full_text += data
                            yield f"data: {json.dumps({'type': 'chunk', 'data': data})}\n\n"
                    elif msg_type == "done":
                        break
                    elif msg_type == "error":
                        error_str = str(data)
                        logger.warning(f"Streaming error: {error_str}")
                        if "GenerateRequestsPerDayPerProject" in error_str:
                            key_rotator.remove_key(current_key)
                        yield f"data: {json.dumps({'type': 'error', 'data': 'Generation interrupted due to quota limit.'})}\n\n"
                        break
                except queue.Empty:
                    continue
                    
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': 'Generation failed.'})}\n\n"

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

        yield f"data: {json.dumps({'type': 'complete', 'citations': citations, 'metrics': metrics})}\n\n"

    def _generate_with_fallback(self, system_instruction: str, user_prompt: str) -> tuple[str, float]:
        import time
        from app.core.config import settings
        max_retries = 2
        total_sleep_time = 0.0
        
        model_name = getattr(settings, "CIVIC_MODEL", "gemini-flash-lite-latest")
        
        for attempt in range(max_retries):
            try:
                current_key = key_rotator.get()
                temp_client = genai.Client(api_key=current_key)
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
                    key_rotator.remove_key(current_key)
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

rag_orchestrator = RAGOrchestrator()

