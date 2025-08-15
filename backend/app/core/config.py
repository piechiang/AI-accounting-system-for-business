from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./accounting.db"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # AI Services
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Classification
    DEFAULT_CLASSIFICATION_MODEL: str = "gpt-3.5-turbo"
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.8
    
    # Reconciliation
    RECONCILIATION_DATE_TOLERANCE_DAYS: int = 3
    RECONCILIATION_FUZZY_MATCH_THRESHOLD: float = 0.85
    
    class Config:
        env_file = ".env"

settings = Settings()