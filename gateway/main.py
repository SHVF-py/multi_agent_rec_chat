import torch
from fastapi import FastAPI
from contextlib import asynccontextmanager

# We import the list of routers we prepared in routers/__init__.py
from routers import all_routers
from services import EmbeddingService, VectorService

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Models are loaded here once and stored in the app state.
    """
    print("🚀 Initializing Unified Compute Gateway...")
    
    # 1. Load Embedding Models (CLIP + SBERT) into memory/GPU
    # Storing in app.state makes them accessible via 'request.app.state'
    app.state.embedding_service = EmbeddingService()
    
    # 2. Initialize FAISS Vector Indexes — one per modality
    # text: BGE-small/SBERT-mini = 384 dims
    # image: CLIP ViT-B-32        = 512 dims
    app.state.vector_service      = VectorService(dimension=384, modality="text")
    app.state.image_vector_service = VectorService(dimension=768, modality="image")  # SigLIP ViT-B/16
    
    print(f"✅ Services initialized. CUDA Available: {torch.cuda.is_available()}")
    
    yield
    
    # Cleanup logic (if any) goes here
    print("🛑 Shutting down Gateway...")

# --- App Definition ---
app = FastAPI(
    title="Unified Compute Gateway",
    description="Dedicated API layer for local LLM, Embeddings, and Vector Search",
    version="1.0.0",
    lifespan=lifespan
)

# --- Router Registration ---
# This automatically handles /llm, /embed, and /vector
for router in all_routers:
    app.include_router(router)

# --- Health Check ---
@app.get("/health", tags=["System"])
async def health():
    """Simple health check to verify gateway and hardware status."""
    return {
        "status": "online",
        "hardware": "cuda" if torch.cuda.is_available() else "cpu"
    }

if __name__ == "__main__":
    import uvicorn
    # Use 1 worker to ensure the GPU memory is managed by a single process
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=False, workers=1)