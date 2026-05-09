"""
Unified Local Gateway for Quiribot
====================================
Runs entirely on CPU. No GPU or PyTorch required.
All inference goes through Ollama (already installed).

Endpoints served (matching the service clients in services/):

  GET  /health                  liveness check
  POST /llm/chat                Ollama phi3 chat completion
  POST /embed/text              Ollama all-minilm text embedding (384-dim)
  POST /vector/text/search      FAISS cosine-similarity search + metadata filter
  POST /vector/text/add         FAISS upsert (insert or update by product_id)

Start:
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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EMBED_MODEL  = "all-minilm"
LLM_MODEL    = "phi3:3.8b"
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
# In-process state
# ---------------------------------------------------------------------------
_state: Dict[str, Any] = {
    "index":    None,
    "metadata": [],
    "vectors":  [],
    "dim":      384,
}


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    import faiss

    logger.info(f"Warming up Ollama embedding model '{EMBED_MODEL}' ...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": "warmup"},
            )
            resp.raise_for_status()
            sample = resp.json()["embeddings"][0]
            _state["dim"] = len(sample)
            logger.info(f"Embedding model ready — dim={_state['dim']}")
    except Exception as exc:
        logger.error(f"Cannot reach Ollama model '{EMBED_MODEL}': {exc}")
        raise

    dim = _state["dim"]

    if INDEX_PATH.exists() and META_PATH.exists() and VECTORS_PATH.exists():
        logger.info("Loading persisted FAISS index from disk ...")
        index = faiss.read_index(str(INDEX_PATH))
        with META_PATH.open() as f:
            metadata: List[Dict] = json.load(f)
        vectors = np.load(str(VECTORS_PATH)).tolist()
        logger.info(f"Loaded {index.ntotal} vectors.")
    else:
        logger.info("No persisted index — creating fresh IndexFlatIP ...")
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
    title="Quiribot Gateway",
    description="Ollama-backed gateway: embeddings + FAISS vector DB + LLM proxy",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize(vec: List[float]) -> np.ndarray:
    arr  = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def _persist() -> None:
    import faiss
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(_state["index"], str(INDEX_PATH))
    with META_PATH.open("w") as f:
        json.dump(_state["metadata"], f, indent=2)
    vecs = _state["vectors"]
    arr  = np.array(vecs, dtype=np.float32) if vecs else np.empty((0, _state["dim"]), dtype=np.float32)
    np.save(str(VECTORS_PATH), arr)


def _matches_filters(meta: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    if filters.get("in_stock") and not meta.get("in_stock", True):
        return False
    price = meta.get("price")
    if price is not None:
        if "price_min" in filters and float(price) < float(filters["price_min"]):
            return False
        if "price_max" in filters and float(price) > float(filters["price_max"]):
            return False
    tenant = filters.get("tenant_id")
    if tenant and meta.get("tenant_id") and meta["tenant_id"] != tenant:
        return False
    return True


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "online", "model": LLM_MODEL, "embed_model": EMBED_MODEL}


# ---------------------------------------------------------------------------
# POST /embed/text   (called by services/embedding_client.py)
# ---------------------------------------------------------------------------
class EmbedTextRequest(BaseModel):
    text: str


@app.post("/embed/text")
async def embed_text(req: EmbedTextRequest):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": req.text},
        )
        resp.raise_for_status()
    vector = resp.json()["embeddings"][0]
    return {"vector": vector}


# ---------------------------------------------------------------------------
# POST /llm/chat   (called by services/llm_client.py)
# ---------------------------------------------------------------------------
class LLMChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float = 0.0
    max_tokens: int = 512


@app.post("/llm/chat")
async def llm_chat(req: LLMChatRequest):
    payload = {
        "model": LLM_MODEL,
        "messages": req.messages,
        "stream": False,
        "options": {
            "temperature": req.temperature,
            "num_predict": req.max_tokens,
        },
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
    text = resp.json()["message"]["content"]
    return {"text": text, "usage": {}}


# ---------------------------------------------------------------------------
# POST /vector/text/add   (called by services/vector_client.py upsert)
# ---------------------------------------------------------------------------
class VectorAddRequest(BaseModel):
    vectors:  List[List[float]]
    metadata: List[Dict[str, Any]]


@app.post("/vector/text/add")
async def vector_add(req: VectorAddRequest):
    import faiss
    index    = _state["index"]
    meta_lst = _state["metadata"]
    vec_lst  = _state["vectors"]

    added = 0
    for vec, meta in zip(req.vectors, req.metadata):
        pid = str(meta.get("product_id", ""))
        tid = str(meta.get("tenant_id", "default"))
        key = f"{tid}:{pid}"

        norm_vec = _normalize(vec)

        # Check if this product already exists → replace
        existing_idx = next(
            (i for i, m in enumerate(meta_lst)
             if str(m.get("product_id", "")) == pid
             and str(m.get("tenant_id", "default")) == tid),
            None,
        )
        if existing_idx is not None:
            vec_lst[existing_idx]  = norm_vec.tolist()
            meta_lst[existing_idx] = meta
            # Rebuild index from scratch (FAISS FlatIP has no in-place update)
            index = faiss.IndexFlatIP(_state["dim"])
            if vec_lst:
                arr = np.array(vec_lst, dtype=np.float32)
                index.add(arr)
            _state["index"] = index
        else:
            index.add(norm_vec.reshape(1, -1))
            vec_lst.append(norm_vec.tolist())
            meta_lst.append(meta)
        added += 1

    _persist()
    return {"added": added}


# ---------------------------------------------------------------------------
# POST /vector/text/search   (called by services/vector_client.py search)
# ---------------------------------------------------------------------------
class VectorSearchRequest(BaseModel):
    vector:  List[float]
    k:       int = 20
    filters: Dict[str, Any] = {}


@app.post("/vector/text/search")
async def vector_search(req: VectorSearchRequest):
    index    = _state["index"]
    meta_lst = _state["metadata"]

    if index.ntotal == 0:
        return {"results": []}

    q = _normalize(req.vector).reshape(1, -1)
    k = min(req.k * 4, index.ntotal)  # over-fetch to allow for filter losses
    scores, indices = index.search(q, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        meta = meta_lst[idx]
        if not _matches_filters(meta, req.filters):
            continue
        results.append({
            "product_id":      meta.get("product_id", str(idx)),
            "similarity_score": float(np.clip(score, 0.0, 1.0)),
            "metadata":        meta,
            "source_type":     meta.get("source_type", "description"),
        })
        if len(results) >= req.k:
            break

    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.main:app", host="0.0.0.0", port=9000, reload=False)
