from fastapi import APIRouter, HTTPException
from models.schemas import LLMRequest, LLMResponse
from services.llm_service import LLMService

router = APIRouter(prefix="/llm", tags=["LLM"])

@router.post("/chat", response_model=LLMResponse)
async def chat(request: LLMRequest):
    # We initialize the service here locally since it's just an HTTP wrapper
    service = LLMService()
    try:
        return await service.chat(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))