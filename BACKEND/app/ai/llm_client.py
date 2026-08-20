import json
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.core.config import settings

logger = logging.getLogger("nyaay_ai")

def get_api_keys():
    # If the user put a comma-separated list in GEMINI_API_KEYS
    keys_str = getattr(settings, 'GEMINI_API_KEYS', None) or os.environ.get('GEMINI_API_KEYS', '')
    if keys_str:
        return [k.strip() for k in keys_str.split(',') if k.strip()]
    # Fallback to single key
    if settings.GEMINI_API_KEY:
        return [settings.GEMINI_API_KEY]
    return []

def generate_with_fallback(*args, **kwargs):
    keys = get_api_keys()
    if not keys:
        raise ValueError("No Gemini API keys found. Please set GEMINI_API_KEYS in .env.")
    
    last_err = None
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            return client.models.generate_content(*args, **kwargs)
        except APIError as e:
            err_msg = str(e)
            if "API key not valid" in err_msg or "INVALID_ARGUMENT" in err_msg or "400" in err_msg or "403" in err_msg or "quota" in err_msg.lower():
                logger.warning(f"Key {key[:8]}... failed with {e.code if hasattr(e, 'code') else 'Error'}. Trying next...")
                last_err = e
                continue
            else:
                # Re-raise if it's a prompt error (e.g., safety block) rather than auth/quota
                raise e
        except Exception as e:
            # For other unexpected exceptions, log and retry
            logger.warning(f"Unexpected error with key {key[:8]}...: {e}. Trying next...")
            last_err = e
            continue
            
    # If all fail
    raise last_err or Exception("All Gemini API keys failed.")

class FallbackModelsWrapper:
    def generate_content(self, *args, **kwargs):
        return generate_with_fallback(*args, **kwargs)

class FallbackGenAIClient:
    def __init__(self):
        self.models = FallbackModelsWrapper()
