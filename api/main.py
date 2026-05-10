import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import QueryInput, OrchestratorOutput, PreprocessingResult, CommentPreprocessingResult
from orchestrator.engine import orchestrator
from preprocessing.pipeline import preprocessing_pipeline
import portal.db as pdb

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

@app.get("/widget/config")
async def widget_config(siteKey: str = Query(..., description="Widget site key")):
    """
    Return the widget configuration for a given site key.
    Called by loader.js before injecting the chat button.
    """
    row = pdb.resolve_site_key(siteKey)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown site key")

    cfg: dict = {}
    try:
        cfg = json.loads(row.get("widget_config") or "{}")
    except Exception:
        pass

    return {
        "tenant_id":     row["id"],
        "bot_name":      cfg.get("bot_name", "Quiribot"),
        "greeting":      cfg.get("greeting", "Hi! How can I help you find the perfect product?"),
        "primary_color": cfg.get("primary_color", "#6366f1"),
        "button_color":  cfg.get("button_color", "#6366f1"),
        "position":      cfg.get("position", "bottom-right"),
        "tone":          cfg.get("tone", "friendly"),
        "avatar_visible":cfg.get("avatar_visible", True),
    }


@app.get("/widget/proactive")
async def widget_proactive(
    siteKey: str = Query(...),
    url:     str = Query("", description="Current page URL on the merchant site"),
):
    """
    Check whether the visitor is on a known product page and return
    a proactive greeting message if so.
    """
    row = pdb.resolve_site_key(siteKey)
    if not row:
        return {"triggered": False, "product_name": None, "message": None}

    tenant_id = row["id"]

    # Read FAISS metadata file directly — no extra service call needed
    import json as _json
    from pathlib import Path
    meta_path = Path("data/faiss_metadata.json")
    if not meta_path.exists():
        return {"triggered": False, "product_name": None, "message": None}

    try:
        meta_list = _json.loads(meta_path.read_text())
        for meta in (meta_list if isinstance(meta_list, list) else meta_list.values()):
            if meta.get("tenant_id") != tenant_id:
                continue
            product_url = meta.get("url", "")
            if product_url and url and product_url.rstrip("/") == url.rstrip("/"):
                name = meta.get("name", "this product")
                return {
                    "triggered":    True,
                    "product_name": name,
                    "message":      f"Looking at {name}? I can answer questions or compare it with similar items!",
                }
    except Exception as exc:
        logger.warning(f"Proactive check failed: {exc}")

    return {"triggered": False, "product_name": None, "message": None}


@app.get("/widget/sync-status")
async def widget_sync_status(siteKey: str = Query(...)):
    """
    Returns whether the tenant's product catalog has been indexed.
    Polled every 5 seconds by the widget's first-time setup screen.
    """
    row = pdb.resolve_site_key(siteKey)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown site key")

    product_count = row.get("product_count") or 0
    if product_count > 0:
        return {
            "is_ready":      True,
            "product_count": product_count,
            "sync_status":   "done",
            "message":       f"{product_count} products ready",
        }

    sync_job = pdb.get_latest_sync(row["id"])
    if sync_job:
        job    = dict(sync_job)
        status = job.get("status", "idle")
        if status == "running":
            return {"is_ready": False, "product_count": 0, "sync_status": "syncing",
                    "message": "Scanning your store for products…"}
        if status == "error":
            return {"is_ready": False, "product_count": 0, "sync_status": "error",
                    "message": job.get("error") or "Sync failed. Retry from your dashboard."}

    return {"is_ready": False, "product_count": 0, "sync_status": "idle",
            "message": "Products not yet synced. Start sync from your dashboard."}


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