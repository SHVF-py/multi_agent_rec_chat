from .llm import router as llm_router
from .embeddings import router as embed_router
from .vector import router as vector_router

# This is the variable main.py is looking for
all_routers = [
    llm_router,
    embed_router,
    vector_router
]