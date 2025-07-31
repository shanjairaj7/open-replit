from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Basic app settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Keys - these will be passed from frontend or environment
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_AI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Project paths
    WORKSPACE_PATH: str = "/app/workspace"
    PROJECTS_PATH: str = "/app/projects"
    BOILERPLATE_PATH: str = "/app/boilerplate"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/bolt_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()