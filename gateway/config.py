class Config:
    # Ollama endpoints (no torch / GPU required)
    OLLAMA_URL   = "http://localhost:11434"
    EMBED_MODEL  = "all-minilm:33m"
    LLM_MODEL    = "phi3:3.8b"

    # Hardware
    DEVICE = "cpu"  # everything runs via Ollama on CPU