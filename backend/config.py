from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./recovery.db"
    ANTHROPIC_API_KEY: Optional[str] = None
    RAZORPAY_KEY_ID: Optional[str] = "rzp_test_mock_key"
    RAZORPAY_KEY_SECRET: Optional[str] = "rzp_test_mock_secret"
    API_AUTH_TOKEN: str = "secret-admin-token"
    GLOBAL_KILL_SWITCH: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
