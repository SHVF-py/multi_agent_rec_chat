from fastapi import APIRouter, Depends, UploadFile, File, Request
from models.schemas import TextEmbedRequest, EmbedResponse

router = APIRouter(prefix="/embed", tags=["Embeddings"])

# Define the dependency locally to avoid circular imports
def get_embed_service(request: Request):
    return request.app.state.embedding_service

@router.post("/text", response_model=EmbedResponse)
async def embed_text(request: TextEmbedRequest, service=Depends(get_embed_service)):
    vector = service.embed_text(request.text)
    return {"vector": vector}

@router.post("/image", response_model=EmbedResponse)
async def embed_image(file: UploadFile = File(...), service=Depends(get_embed_service)):
    vector = service.embed_image(file)
    return {"vector": vector}