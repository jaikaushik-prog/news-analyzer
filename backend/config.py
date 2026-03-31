import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/postgres"
    ANTHROPIC_API_KEY: str = ""
    
    # Constants
    SECTORS: list[str] = [
        "Tech", "Finance", "Healthcare", "Energy", "Consumer", "Industrials", "Materials"
    ]
    
    SECTOR_COLORS: dict[str, str] = {
        "Tech": "#3b82f6",
        "Finance": "#10b981",
        "Healthcare": "#ec4899",
        "Energy": "#f59e0b",
        "Consumer": "#8b5cf6",
        "Industrials": "#64748b",
        "Materials": "#f97316"
    }

    class Config:
        env_file = ".env"

settings = Settings()
