import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'recovery.db')}"

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = DEFAULT_DB_URL
    
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    GROQ_MODEL: str = "groq/compound-mini"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    RAZORPAY_KEY_ID: Optional[str] = "rzp_test_mock_key"
    RAZORPAY_KEY_SECRET: Optional[str] = "rzp_test_mock_secret"
    API_AUTH_TOKEN: str = "secret-admin-token"
    GLOBAL_KILL_SWITCH: bool = False
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
if settings.DATABASE_URL == "sqlite+aiosqlite:///./recovery.db":
    settings.DATABASE_URL = DEFAULT_DB_URL

