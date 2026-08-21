"""
core/key_rotator.py — Round-robin Gemini API key rotation.

Multiplies effective free-tier RPM by the number of keys provided.
Add keys to .env as a comma-separated list:
    GEMINI_API_KEYS=key1,key2,key3

Falls back to GEMINI_API_KEY if GEMINI_API_KEYS is not set.
"""
import threading
import logging
from typing import List

logger = logging.getLogger(__name__)


class APIKeyRotator:
    """Thread-safe round-robin API key rotator."""

    def __init__(self, keys: List[str]):
        valid = [k.strip() for k in keys if k and k.strip()]
        if not valid:
            raise ValueError("APIKeyRotator requires at least one valid API key.")
        self._keys = valid
        self._index = 0
        self._lock = threading.Lock()
        logger.info(f"APIKeyRotator initialised with {len(self._keys)} key(s).")

    def get(self) -> str:
        """Return the next API key in round-robin order."""
        with self._lock:
            if not self._keys:
                raise ValueError("All API keys have been exhausted for the day.")
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key

    def remove_key(self, key: str):
        """Remove a permanently dead/daily-exhausted key from the pool."""
        with self._lock:
            if key in self._keys:
                self._keys.remove(key)
                logger.warning(f"Key {key[:10]}... removed from rotation due to daily quota exhaustion. {len(self._keys)} keys remaining.")

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._keys)


def build_rotator_from_settings() -> APIKeyRotator:
    """
    Build the rotator from app settings.
    Prefers GEMINI_API_KEYS (comma-separated); falls back to GEMINI_API_KEY.
    """
    from app.core.config import settings

    keys: List[str] = []

    # GEMINI_API_KEYS takes priority (comma-separated multi-key list)
    if settings.GEMINI_API_KEYS:
        keys = [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]

    # Fall back to single key
    if not keys and settings.GEMINI_API_KEY:
        keys = [settings.GEMINI_API_KEY]

    if not keys:
        raise ValueError(
            "No Gemini API keys found. Set GEMINI_API_KEY or GEMINI_API_KEYS in .env"
        )

    return APIKeyRotator(keys)


# Singleton — imported by orchestrators
key_rotator = build_rotator_from_settings()
