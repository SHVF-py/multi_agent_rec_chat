from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import QueryInput, OrchestratorOutput, PreprocessingResult, CommentPreprocessingResult
from orchestrator.engine import orchestrator
from preprocessing.pipeline import preprocessing_pipeline
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Quiribot API starting...")
    yield
    logger.info("Quiribot API shutting down...")

app = FastAPI(
    title="Quiribot API",
    description="Multi-Agent E-Commerce Recommendation System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "quiribot"}

@app.post("/query", response_model=OrchestratorOutput)
async def query_endpoint(request: QueryInput):
    """
    Main query endpoint.

    Accepts user query and returns recommendations.
    The query is preprocessed (cleaned, normalized, price hints extracted)
    before being passed to the multi-agent orchestrator.
    """
    logger.info(f"Received query: {request.query_text}")

    # --- Text Preprocessing (runs before multi-agent system) ---
    prep = preprocessing_pipeline.process(request.query_text)

    if not prep.is_valid:
        raise HTTPException(
            status_code=400,
            detail=prep.warnings[0] if prep.warnings else "Invalid query.",
        )

    if prep.warnings:
        logger.warning(f"Preprocessing warnings for query '{request.query_text}': {prep.warnings}")

    # Replace raw query with the cleaned, normalized version
    request.query_text = prep.normalized_query

    # Attach preprocessing metadata for downstream agents
    request.preprocessing = PreprocessingResult(
        original_query=prep.original_query,
        cleaned_query=prep.cleaned_query,
        normalized_query=prep.normalized_query,
        price_hints=prep.price_hints,
        detected_brands=prep.detected_brands,
        detected_categories=prep.detected_categories,
        is_valid=prep.is_valid,
        warnings=prep.warnings,
    )

    logger.info(
        f"Preprocessed query: '{prep.normalized_query}' | "
        f"brands={prep.detected_brands} | "
        f"categories={prep.detected_categories} | "
        f"price_hints={prep.price_hints}"
    )

    try:
        result = await orchestrator.execute(request)
        return result

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Quiribot",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)