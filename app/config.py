import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dhanvantari AI Doctor"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_doctor.db"
    
    # LLM Settings
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY", None)
    GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY", None)
    OPENROUTER_MODEL_NAME: str = os.getenv("OPENROUTER_MODEL_NAME", "deepseek/deepseek-r1")
    VISION_MODEL_NAME: str = os.getenv("VISION_MODEL_NAME", "google/gemini-2.0-flash-001")
    MEDGEMMA_API_BASE: str | None = os.getenv("MEDGEMMA_API_BASE", None)
    GEMMA_MODEL_NAME: str = "gemma-2-9b-it"
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    HF_TOKEN: str | None = os.getenv("HF_TOKEN", None)
    MEDGEMMA_HF_MODEL_ID: str = "google/medgemma-1.5-4b-it"
    VIBEVOICE_MODEL_ID: str = os.getenv("VIBEVOICE_MODEL_ID", "tarun7r/vibevoice-hindi-1.5B")
    
    # Reasoning & Escalation Settings
    R1_ESCALATION_ENABLED: bool = True
    DIFF_ENTROPY_THRESHOLD: float = 0.15
    
    # Active mode settings
    # Default fallback to mock if no API keys are present
    MOCK_LLM: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
