from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "BreatheWise"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./breathewise.db"

    # Qdrant Vector Database
    QDRANT_URL: str = ":memory:"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "breathewise_knowledge"

    # Google Gemini (LLM + Embeddings)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LOCAL_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Retrieval defaults
    RETRIEVAL_MODE: str = "hybrid"  # dense | bm25 | hybrid
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SCORE_THRESHOLD: float = 0.25
    ENABLE_RERANKER: bool = False

    # Security & Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 120

    # Air Quality Providers
    OPEN_METEO_AQI_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_GEOCODE_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    CPCB_API_KEY: str = ""
    CPCB_API_URL: str = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    AQI_CACHE_TTL_SECONDS: int = 600

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def cpcb_configured(self) -> bool:
        return bool(self.CPCB_API_KEY and self.CPCB_API_KEY.strip() and self.CPCB_API_URL.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
