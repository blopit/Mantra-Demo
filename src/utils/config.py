"""
Configuration settings for the application.
"""

import os
from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    
    # Database Pool
    POOL_SIZE: int = int(os.getenv("POOL_SIZE", "5"))
    MAX_OVERFLOW: int = int(os.getenv("MAX_OVERFLOW", "10"))
    POOL_TIMEOUT: int = int(os.getenv("POOL_TIMEOUT", "30"))
    POOL_RECYCLE: int = int(os.getenv("POOL_RECYCLE", "1800"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "True").lower() == "true"
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:8765")
    
    # Flask
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "your-secret-key-here")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    OAUTHLIB_INSECURE_TRANSPORT: str = os.getenv("OAUTHLIB_INSECURE_TRANSPORT", "1")
    
    # User
    DEMO_USER_ID: str = os.getenv("DEMO_USER_ID", "")
    
    # Services
    GMAIL_CACHE_TTL_MINUTES: int = int(os.getenv("GMAIL_CACHE_TTL_MINUTES", "15"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MEMORY_DB_PATH: str = os.getenv("MEMORY_DB_PATH", "agent_memory.db")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # N8N
    N8N_API_URL: str = os.getenv("N8N_API_URL", "http://localhost:5678/api/v1")
    N8N_API_KEY: str = os.getenv("N8N_API_KEY", "your-api-key")
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 