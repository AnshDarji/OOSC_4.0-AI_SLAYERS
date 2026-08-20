import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./nyaay.db"

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = "nyaay-ai"
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "BACKEND/secrets/serviceAccountKey.json"

    # App Settings
    ENVIRONMENT: str = "development"
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""
    MIN_RETRIEVAL_THRESHOLD: float = 0.015
    # Firebase UIDs permitted to view operational metrics. Keep empty by
    # default so metrics are never exposed accidentally.
    ADMIN_UIDS: List[str] = []

    # CORS Allowed Origins
    # Comma-separated or list of origins. Development defaults provided.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    model_config = SettingsConfigDict(
        # Load from .env at the BACKEND root directory
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def firebase_service_account_absolute_path(self) -> str:
        path_str = self.FIREBASE_SERVICE_ACCOUNT_PATH.replace("\\", "/")
        path = Path(path_str)
        if path.is_absolute():
            return str(path)

        # Derive path based on backend directory
        backend_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # BACKEND/
        workspace_dir = backend_dir.parent # Root/

        if path_str.startswith("BACKEND/"):
            # If path includes BACKEND/ prefix, resolve from workspace root
            return str((workspace_dir / path_str).resolve())
        else:
            # Otherwise resolve directly from backend root
            return str((backend_dir / path_str).resolve())

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

settings = Settings()
