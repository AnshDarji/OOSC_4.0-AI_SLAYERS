from app.models.chat import Conversation
from app.database.database import SessionLocal
from google import genai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def generate_conversation_title_async(conversation_id: str, prompt: str):
    """
    Background task to generate a concise 3-6 word title using the LLM.
    """
    try:
        from app.ai.llm_client import get_api_keys
        keys = get_api_keys()
        api_key = keys[0] if keys else "DUMMY_KEY_FOR_TESTING"
        client = genai.Client(api_key=api_key)
        
        system_instruction = "You are an AI that generates concise conversation titles. Generate a 3-6 word title based on the user's prompt. Only return the title, no quotes or extra text."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        
        new_title = response.text.strip().strip('"')
        
        if new_title:
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

