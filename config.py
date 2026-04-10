"""
Application configuration using environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = "credentials/google_credentials.json"
    GOOGLE_SHEET_ID: str = ""  # Your target Google Sheet ID
    GOOGLE_SHEET_NAME: str = "Orders"  # Tab/worksheet name

    # OpenAI (optional — for LLM-powered parsing)
    OPENAI_API_KEY: Optional[str] = None
    USE_LLM_PARSING: bool = False  # Set True to use OpenAI for parsing

    # Upload limits
    MAX_FILE_SIZE_MB: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
