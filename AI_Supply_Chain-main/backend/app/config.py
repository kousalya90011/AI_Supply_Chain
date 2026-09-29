from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Supply Chain Risk Intelligence Assistant"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str = "sqlite:///./supply_chain.db"

    JWT_SECRET_KEY: str = "supply-chain-dev-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    DATA_DIR: str = "../../data"
    RAW_DATA_DIR: str = "../../data/raw"
    PROCESSED_DATA_DIR: str = "../../data/processed"

    # LLM configuration
    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # Optional fallback LLM
    FALLBACK_LLM_BASE_URL: str = ""
    FALLBACK_LLM_API_KEY: str = ""
    FALLBACK_LLM_MODEL: str = ""

    # Risk scoring
    DELAY_WEIGHT: float = 0.40
    ROUTE_WEIGHT: float = 0.20
    UNITS_WEIGHT: float = 0.20
    COST_WEIGHT: float = 0.10
    HANDLING_WEIGHT: float = 0.10

    # Confidence
    HIGH_CONFIDENCE_THRESHOLD: float = 0.80
    LOW_CONFIDENCE_THRESHOLD: float = 0.50

    # Guardrails Configuration
    MAX_QUERY_LENGTH: int = 500
    MAX_TOP_K: int = 5
    MAX_EVIDENCE_ITEMS: int = 15
    MIN_RETRIEVAL_SCORE: float = 0.05
    ENABLE_INPUT_GUARDRAILS: bool = True
    ENABLE_SCOPE_GUARDRAIL: bool = True
    ENABLE_RAG_GUARDRAILS: bool = True
    ENABLE_OUTPUT_GUARDRAILS: bool = True
    ENABLE_GROUNDING_GUARDRAIL: bool = True

    # Retrieval & Embeddings Configuration
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_STORE: str = "local"
    SEMANTIC_TOP_K: int = 5
    STRUCTURED_TOP_K: int = 5
    HYBRID_ALPHA: float = 0.5
    HYBRID_BETA: float = 0.5
    VECTOR_STORE_DIR: str = "../../data/knowledge_base"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


def get_project_root() -> Path:
    """
    Returns the root directory of the project.
    """
    return Path(__file__).resolve().parents[2]


def get_raw_data_path() -> Path:
    return get_project_root() / "data" / "raw"


def get_processed_data_path() -> Path:
    return get_project_root() / "data" / "processed"