from app.models.chat import Conversation
from app.database.database import SessionLocal
import logging
import re

logger = logging.getLogger(__name__)

def generate_deterministic_title(prompt: str) -> str:
    """
    Deterministic local title generator.
    0 LLM calls, <1ms processing, 5-7 words max.
    """
    prompt = prompt.strip()
    if not prompt:
        return "New Civic Inquiry"
        
    # Rules based on keywords
    lower_prompt = prompt.lower()
    if "landlord" in lower_prompt or "rent" in lower_prompt or "tenant" in lower_prompt:
        if "lock" in lower_prompt or "evict" in lower_prompt:
            return "Landlord Eviction / Lockout"
        return "Tenant Rights Inquiry"
    elif "rti" in lower_prompt or "information" in lower_prompt:
        return "RTI Application Inquiry"
    elif "amazon" in lower_prompt or "flipkart" in lower_prompt or "refund" in lower_prompt or "defective" in lower_prompt or "broken" in lower_prompt or "seller" in lower_prompt:
        return "Consumer Dispute / Refund"
    elif "salary" in lower_prompt or "employer" in lower_prompt or "work" in lower_prompt:
        return "Workplace Rights Inquiry"
    
    # Fallback: clean up the prompt and take first 5 words
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', prompt)
    words = cleaned.split()
    if not words:
        return "New Civic Inquiry"
        
    title = " ".join(words[:5]).title()
    return title

def generate_conversation_title_async(conversation_id: str, prompt: str):
    """
    Background task to generate a title deterministically and save it to the DB.
    """
    try:
        new_title = generate_deterministic_title(prompt)
        
        db = SessionLocal()
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.title = new_title
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to generate title asynchronously: {e}")
