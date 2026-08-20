from app.knowledge.hybrid_retriever import hybrid_retriever
from app.knowledge.embeddings import embedding_service
from app.core.config import settings
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
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing in settings")
        self.client = genai.Client(api_key=api_key)
        
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
            res = self.client.models.generate_content(
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
                    # Do not return a validator error message as if it were a
                    # legal answer when the retry also fails validation.
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
            # 8. Sidebar Filtering & Explainability
            if marker_num in used_citations:
                meta = chunk.get("metadata", {})
                src_name = meta.get("source_name", "Unknown")
                domain = meta.get("legal_domain", "")
                
                # Relies strictly on metadata from ingestion
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

        # Format confidence for the UI with safety fallbacks
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

    def _generate_with_fallback(self, system_instruction: str, user_prompt: str) -> tuple[str, float]:
        import time
        max_retries = 3
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-lite-latest']
        total_sleep_time = 0.0
        
        for attempt in range(max_retries):
            model_name = models_to_try[attempt % len(models_to_try)]
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.client.models.generate_content,
                        model=model_name,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        ),
                    )
                    # Increased timeout to 45s for complex reasoning tasks
                    response = future.result(timeout=45)
                return response.text.strip(), total_sleep_time
            except concurrent.futures.TimeoutError:
                logger.warning(f"RAG Generation with {model_name} timed out.")
                continue
            except Exception as e:
                error_str = str(e)
                logger.warning(f"RAG Generation with {model_name} failed: {error_str}")
                
                # Handle Exponential Backoff for Rate Limits
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    sleep_time = 2 ** attempt * 5  # 5s, 10s, 20s
                    logger.info(f"Rate limited. Applying exponential backoff: sleeping for {sleep_time}s.")
                    time.sleep(sleep_time)
                    total_sleep_time += sleep_time
                continue
                
        return None, total_sleep_time

    def _fallback_response(self, message: str) -> Dict[str, Any]:
        return {
            "answer": message,
            "citations": [],
            # All API response schemas consume confidence as structured data.
            # Keeping the fallback shape identical prevents upstream outages
            # from becoming response-validation 500s.
            "confidence": {
                "level": "🔴 Insufficient",
                "reason": message,
            },
            "metrics": {}
        }

rag_orchestrator = RAGOrchestrator()
