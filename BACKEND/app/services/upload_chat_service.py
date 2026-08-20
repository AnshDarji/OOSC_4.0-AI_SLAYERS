import json
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.chat import Conversation, Message, FeatureType, MessageRole
from app.schemas.upload_chat import ChatQueryRequest, ChatQueryResponse
from app.core.config import settings
from google import genai
from google.genai import types

class UploadChatService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or "DUMMY_KEY_FOR_TESTING"
        self.client = genai.Client(api_key=api_key)

    def query(self, request: ChatQueryRequest, db: Session, user_uid: str, background_tasks) -> ChatQueryResponse:
        from app.ai.orchestrator import rag_orchestrator
        from app.services.title_service import generate_conversation_title_async
        import json
        
        # 1. Verify Document Access
        doc = db.query(Document).filter(Document.id == request.document_id, Document.user_uid == user_uid).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found or access denied.")
            
        # 2. Conversation Persistence
        conversation = None
        
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_uid
            ).first()

            if conversation and (
                conversation.feature_type != FeatureType.upload_chat
                or conversation.document_id != request.document_id
            ):
                raise HTTPException(status_code=400, detail="Conversation does not belong to this document chat.")
                        
        if not conversation:
            title = "New Conversation"
            conversation = Conversation(
                user_id=user_uid,
                title=title,
                feature_type=FeatureType.upload_chat,
                document_id=request.document_id
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            background_tasks.add_task(generate_conversation_title_async, conversation.id, request.question)

        # Save User Message
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=request.question
        )
        db.add(user_msg)
        db.commit()

        # Load real history from DB instead of empty array
        past_messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
        # the history parameter is expecting list of dicts. We skip the very last message which is the current user_msg.
        formatted_history = [{"role": m.role.value, "content": m.content} for m in past_messages[:-1]]

        # 3. Prompt RAG Orchestrator
        filters = {
            "$and": [
                {"document_id": request.document_id},
                {"tenant_id": user_uid}
            ]
        }
        
        response_data = rag_orchestrator.trigger_pipeline(
            question=request.question,
            filters=filters,
            history=formatted_history
        )
        
        # Merge summary logic for backwards compatibility with the UI
        raw_answer = response_data.get("answer", "No answer generated.")
        
        import re
        exec_summary_match = re.search(r'(?i)##\s*Executive Summary\s*\n(.*?)(?=\n##|\Z)', raw_answer, re.DOTALL)
        if exec_summary_match:
            dynamic_summary = exec_summary_match.group(1).strip()
            raw_answer = raw_answer[:exec_summary_match.start()] + raw_answer[exec_summary_match.end():]
        else:
            paragraphs = [p.strip() for p in raw_answer.split('\n') if p.strip() and not p.strip().startswith('#')]
            dynamic_summary = paragraphs[0] if paragraphs else "Response based on retrieved document chunks."
            if len(dynamic_summary) > 250:
                dynamic_summary = dynamic_summary[:247] + "..."
            
        response_data["summary"] = dynamic_summary
        response_data["answer"] = raw_answer
        
        # Save Assistant Message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=json.dumps(response_data)
        )
        db.add(assistant_msg)
        db.commit()
        
        return ChatQueryResponse(conversation_id=conversation.id, **response_data)

    def _filter_chunks(self, question: str, chunks: list[str]) -> str:
        # Very basic stop word removal
        stop_words = {"what", "are", "is", "the", "a", "an", "of", "and", "in", "to", "for", "with", "on", "my", "this", "can", "do", "does", "how", "why", "where"}
        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        if not keywords:
            # Fallback to returning beginning and end if no keywords
            return "\n\n".join(chunks[:10] + chunks[-10:])
            
        # Score chunks based on keyword hits
        scored_chunks = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for kw in keywords if kw in chunk_lower)
            if score > 0:
                scored_chunks.append((score, chunk))
                
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Take top 30 chunks
        top_chunks = [c[1] for c in scored_chunks[:30]]
        
        if not top_chunks:
            # Fallback
            return "\n\n".join(chunks[:20])
            
        return "\n\n".join(top_chunks)

upload_chat_service = UploadChatService()
