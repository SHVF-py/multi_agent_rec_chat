from fastapi import APIRouter, Depends, Request
from models.schemas import VectorAddRequest, VectorSearchRequest, SearchResponse

router = APIRouter(prefix="/vector", tags=["Vector"])

def get_text_vec_service(request: Request):
    return request.app.state.vector_service

def get_image_vec_service(request: Request):
    return request.app.state.image_vector_service

# --- Text index (384-dim) ---
@router.post("/text/add")
async def add_text_vector(request: VectorAddRequest, service=Depends(get_text_vec_service)):
    return service.add_vectors(request.vectors, request.metadata)

@router.post("/text/search", response_model=SearchResponse)
async def search_text_vector(request: VectorSearchRequest, service=Depends(get_text_vec_service)):
    results = service.search(request.vector, request.k, filters=request.filters)
    return {"results": results}

# --- Image index (512-dim) ---
@router.post("/image/add")
async def add_image_vector(request: VectorAddRequest, service=Depends(get_image_vec_service)):
    return service.add_vectors(request.vectors, request.metadata)

@router.post("/image/search", response_model=SearchResponse)
async def search_image_vector(request: VectorSearchRequest, service=Depends(get_image_vec_service)):
    results = service.search(request.vector, request.k)
    return {"results": results}