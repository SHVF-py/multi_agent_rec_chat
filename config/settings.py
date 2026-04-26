from pydantic_settings import BaseSettings
from typing import Optional

_NGROK_BASE = "https://uninoculated-thurman-beautifully.ngrok-free.dev"

class Settings(BaseSettings):
    # Unified local gateway (gateway/main.py running on port 9000).
    # All three services (LLM, Embedding, Vector DB) are served from one process.
    HOST_LLM_URL: str = "http://localhost:9000"
    HOST_EMBEDDING_URL: str = "http://localhost:9000"
    HOST_VECTOR_URL: str = "http://localhost:9000"

    # External product catalog APIs
    FAKESTORE_API_URL: str = "https://fakestoreapi.com"

    # Ngrok tunnel URL — kept for when the host PC setup is used again.
    NGROK_API_URL: str = _NGROK_BASE
    
    # API Keys (if host requires authentication)
    HOST_API_KEY: Optional[str] = None
    
    # Timeouts (seconds)
    LLM_TIMEOUT: int = 180
    EMBEDDING_TIMEOUT: int = 30
    VECTOR_TIMEOUT: int = 15

    # Orchestrator
    ORCHESTRATOR_TIMEOUT: int = 300
    
    # Retrieval settings
    DEFAULT_TOP_K: int = 20
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.1
    
    # Query understanding
    CONFIDENCE_THRESHOLD: float = 0.3
    
    # Ranking weights
    WEIGHT_RELEVANCE: float = 0.4
    WEIGHT_CONSTRAINTS: float = 0.25
    WEIGHT_RATING: float = 0.15
    WEIGHT_PERSONALIZATION: float = 0.15
    WEIGHT_STOCK: float = 0.05
    
    # MBA settings
    MBA_RULES_PATH: str = "data/association_rules.json"
    MBA_MIN_CONFIDENCE: float = 0.3
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()