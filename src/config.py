"""Configuration management for the RAG system."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

# Load environment variables from the project root .env file when present.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    openai_api_key: str = Field(default="dummy_key_ollama", alias="OPENAI_API_KEY")
    chroma_persist_dir: str = Field(default="./chroma_db", alias="CHROMA_PERSIST_DIR")
    top_k_retrieval: int = Field(default=10, alias="TOP_K_RETRIEVAL")
    top_k_rerank: int = Field(default=3, alias="TOP_K_RERANK")
    faithfulness_threshold: float = Field(default=0.75, alias="FAITHFULNESS_THRESHOLD")
    ollama_host: str = Field(default="http://rag-ollama:11434", alias="OLLAMA_HOST")
    admin_api_key: str = Field(default="", alias="ADMIN_API_KEY")
    enable_unauth_admin: bool = Field(default=False, alias="RAG_ENABLE_UNAUTHED_ADMIN")
    refusal_confidence_enabled: bool = Field(default=True, alias="RAG_REFUSAL_CONFIDENCE_ENABLED")
    refusal_confidence_threshold: float = Field(default=0.18, alias="RAG_REFUSAL_CONFIDENCE_THRESHOLD")
    force_fallback_on_model_refusal: bool = Field(default=False, alias="RAG_FORCE_FALLBACK_ON_MODEL_REFUSAL")
    force_fallback_confidence_threshold: float = Field(
        default=0.55,
        alias="RAG_FORCE_FALLBACK_CONFIDENCE_THRESHOLD",
    )


settings = Settings()
