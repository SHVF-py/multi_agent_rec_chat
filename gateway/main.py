"""
Unified Local Gateway for Quiribot Demo
========================================
Runs entirely on CPU. No GPU required.
Zero Python ML libraries — embeddings and LLM both go through Ollama HTTP.

Exposes the same HTTP API that the three service clients already expect:

  GET  /health                 -> liveness check
  POST /embed                  -> Ollama all-minilm embeddings (384-dim)
  POST /upsert                 -> store vector + metadata in FAISS (persisted to disk)
  POST /search                 -> FAISS cosine-similarity search + metadata filtering
  POST /v1/chat/completions    -> proxied to Ollama (phi3)

One-time setup:
    python -m venv .venv
    .venv\\Scripts\\activate
    pip install fastapi "uvicorn[standard]" httpx numpy faiss-cpu
    ollama pull all-minilm
    ollama pull phi3

Start with (from inside .venv):
    uvicorn gateway.main:app --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EMBED_MODEL  = "all-minilm"    # Ollama model — 384-dim, ~45 MB, fast on CPU
EMBED_DIM    = 384             # all-minilm output dimension
OLLAMA_URL   = "http://localhost:11434"
INDEX_PATH   = Path("data/faiss_index.bin")
META_PATH    = Path("data/faiss_metadata.json")
VECTORS_PATH = Path("data/faiss_vectors.npy")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gateway")

# ---------------------------------------------------------------------------
# Shared mutable state (populated at startup)
# ---------------------------------------------------------------------------
_state: Dict[str, Any] = {
    "index":    None,   # faiss.IndexFlatIP
    "metadata": [],     # List[Dict]  — parallel to FAISS vectors
    "vectors":  [],     # List[List[float]] — for index rebuilds on duplicate upsert
    "dim":      EMBED_DIM,
}


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    import faiss

    # Verify Ollama embedding model is reachable before accepting traffic
    logger.info(f"Warming up Ollama embedding model '{EMBED_MODEL}' …")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": "warmup"},
            )
            resp.raise_for_status()
            sample = resp.json()["embeddings"][0]
            actual_dim = len(sample)
            logger.info(f"Ollama embed OK — dim={actual_dim}")
            _state["dim"] = actual_dim
    except Exception as exc:
        logger.error(
            f"Cannot reach Ollama embedding model '{EMBED_MODEL}': {exc}\n"
            "Run: ollama pull all-minilm"
        )
        raise

    dim = _state["dim"]

    # Load persisted index if it exists
    if INDEX_PATH.exists() and META_PATH.exists() and VECTORS_PATH.exists():
        logger.info("Loading persisted FAISS index from disk …")
        index = faiss.read_index(str(INDEX_PATH))
        with META_PATH.open() as f:
            metadata: List[Dict] = json.load(f)
        vectors = np.load(str(VECTORS_PATH)).tolist()
        logger.info(f"Loaded {index.ntotal} vectors.")
    else:
        logger.info("No persisted index found — creating fresh IndexFlatIP …")
        index    = faiss.IndexFlatIP(dim)
        metadata = []
        vectors  = []

    _state["index"]    = index
    _state["metadata"] = metadata
    _state["vectors"]  = vectors

    logger.info("Gateway ready.")
    yield

    logger.info("Gateway shutting down.")


app = FastAPI(
    title="Quiribot Local Gateway",
    description="Unified local gateway: embeddings (sentence-transformers) + vector DB (FAISS) + LLM (Ollama phi3)",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _normalize(vec: List[float]) -> np.ndarray:
    arr  = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def _persist() -> None:
    """Write FAISS index + metadata + raw vectors to disk."""
    import faiss
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(_state["index"], str(INDEX_PATH))
    with META_PATH.open("w") as f:
        json.dump(_state["metadata"], f, indent=2)
    vecs = _state["vectors"]
    arr  = np.array(vecs, dtype=np.float32) if vecs else np.empty((0, _state["dim"]), dtype=np.float32)
    np.save(str(VECTORS_PATH), arr)


def _rebuild_index(keep_indices: List[int]) -> None:
    """Rebuild the FAISS index keeping only the specified entry positions."""
    import faiss
    dim      = _state["dim"]
    new_idx  = faiss.IndexFlatIP(dim)
    old_vecs = _state["vectors"]
    old_meta = _state["metadata"]

    kept_vecs = [old_vecs[i] for i in keep_indices]
    kept_meta = [old_meta[i] for i in keep_indices]

    if kept_vecs:
        new_idx.add(np.array(kept_vecs, dtype=np.float32))

    _state["index"]    = new_idx
    _state["vectors"]  = kept_vecs
    _state["metadata"] = kept_meta


def _passes_filters(meta: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Return True if product metadata satisfies all active filters."""
    # Stock
    if filters.get("in_stock") is True and not meta.get("in_stock", True):
        return False
    # Price
    price = meta.get("price")
    if price is not None:
        price = float(price)
        if "price_min" in filters and price < float(filters["price_min"]):
            return False
        if "price_max" in filters and price > float(filters["price_max"]):
            return False
    # Brand (case-insensitive)
    if "brand" in filters:
        if meta.get("brand", "").lower() != str(filters["brand"]).lower():
            return False
    # Category (case-insensitive)
    if "category" in filters:
        if meta.get("category", "").lower() != str(filters["category"]).lower():
            return False
    return True


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class EmbedRequest(BaseModel):
    input: str
    model: Optional[str] = None


class UpsertRequest(BaseModel):
    product_id: str
    vector: List[float]
    metadata: Dict[str, Any]
    tenant_id: str


class SearchRequest(BaseModel):
    vector: List[float]
    top_k: int = 20
    filters: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    index = _state.get("index")
    return {
        "status":          "healthy",
        "service":         "quiribot-local-gateway",
        "vectors_indexed": index.ntotal if index is not None else 0,
        "embed_model":     f"ollama/{EMBED_MODEL}",
        "llm":             "ollama/phi3",
    }


@app.post("/embed")
async def embed(req: EmbedRequest):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": req.input},
            )
            resp.raise_for_status()
            vec: List[float] = resp.json()["embeddings"][0]
            return {"embedding": vec, "model": EMBED_MODEL}
    except httpx.ConnectError:
        raise HTTPException(503, "Ollama not reachable — is 'ollama serve' running?")
    except httpx.TimeoutException:
        raise HTTPException(504, "Ollama embed timed out")
    except (KeyError, IndexError):
        raise HTTPException(502, "Unexpected response from Ollama embed endpoint")


@app.post("/upsert")
def upsert(req: UpsertRequest):
    index    = _state["index"]
    metadata = _state["metadata"]
    vectors  = _state["vectors"]

    # Remove any existing entry for this product_id + tenant_id (idempotent upsert)
    keep = [
        i for i, m in enumerate(metadata)
        if not (m.get("product_id") == req.product_id
                and m.get("tenant_id") == req.tenant_id)
    ]
    if len(keep) < len(metadata):
        _rebuild_index(keep)
        index    = _state["index"]
        metadata = _state["metadata"]
        vectors  = _state["vectors"]

    # Add new entry
    vec = _normalize(req.vector)
    index.add(vec.reshape(1, -1))
    metadata.append({
        **req.metadata,
        "product_id": req.product_id,
        "tenant_id":  req.tenant_id,
    })
    vectors.append(vec.tolist())

    _persist()
    logger.info(f"Upserted product_id={req.product_id!r}  tenant={req.tenant_id!r}  "
                f"(index size: {index.ntotal})")
    return {"status": "ok", "product_id": req.product_id}


@app.post("/search")
def search(req: SearchRequest):
    index    = _state.get("index")
    metadata = _state.get("metadata", [])

    if index is None or index.ntotal == 0:
        return {"results": []}

    vec = _normalize(req.vector).reshape(1, -1)

    # Over-fetch to leave room after filtering
    k = min(index.ntotal, max(req.top_k * 5, 50))
    scores, indices = index.search(vec, k)

    tenant_id = req.filters.get("tenant_id", "default")
    results: List[Dict] = []
    seen: set = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        meta = metadata[idx]
        pid  = meta.get("product_id", "")

        # Dedup (safety net for any duplicate entries)
        if pid in seen:
            continue
        # Tenant isolation
        if meta.get("tenant_id", "default") != tenant_id:
            continue
        # Metadata filters
        if not _passes_filters(meta, req.filters):
            continue

        seen.add(pid)
        results.append({
            "product_id":       pid,
            "similarity_score": float(np.clip(score, 0.0, 1.0)),
            "source_type":      meta.get("source_type", "description"),
            "timestamp":        meta.get("timestamp", ""),
            "metadata":         meta,
        })

        if len(results) >= req.top_k:
            break

    logger.info(f"Search returned {len(results)} results (tenant={tenant_id!r})")
    return {"results": results}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Proxy to Ollama's OpenAI-compatible endpoint.
    Translates OpenAI's response_format → Ollama's format field.
    """
    payload = await request.json()

    # Always route to the locally installed phi3 model
    payload["model"] = "phi3:3.8b"

    # Pass response_format through unchanged — Ollama's /v1/chat/completions
    # supports it natively (same as the OpenAI spec).

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    except httpx.ConnectError:
        raise HTTPException(
            503,
            "Ollama is not reachable. Make sure 'ollama serve' is running on localhost:11434."
        )
    except httpx.TimeoutException:
        raise HTTPException(504, "Ollama request timed out (LLM is slow on CPU — this is normal).")
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"Ollama error: {e.response.text}")
