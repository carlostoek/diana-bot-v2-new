"""
Configuration file for the Diana Bot project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings:
    """
    Application settings loaded from environment variables.
    """
    # Core settings
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # --- PostgreSQL Database (temporarily disabled) ---
    # POSTGRES_HOST: str = os.getenv('POSTGRES_HOST', 'localhost')
    # POSTGRES_PORT: int = int(os.getenv('POSTGRES_PORT', 5432))
    # POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'user')
    # POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', 'password')
    # POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'diana_db')
    # DATABASE_URL: str = (
    #     f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    #     f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    # )

    # --- SQLite Database (temporary) ---
    DATABASE_URL: str = f"sqlite+aiosqlite:///{PROJECT_ROOT}/diana_bot.db"

    # Redis
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB: int = int(os.getenv('REDIS_DB', 0))

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', 'your_token_here')

    # Debug and Testing
    DEBUG: bool = ENVIRONMENT == 'development'
    TESTING: bool = ENVIRONMENT == 'testing'


# Instantiate the settings
settings = Settings()
