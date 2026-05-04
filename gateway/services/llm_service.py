import httpx
from config import Config
from models.schemas import LLMRequest, LLMResponse

class LLMService:
    async def chat(self, payload: LLMRequest) -> LLMResponse:
        vllm_payload = {
            "model": Config.MODEL_NAME,
            "messages": payload.messages,
            "temperature": payload.temperature,
            "max_tokens": payload.max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(Config.VLLM_URL, json=vllm_payload)
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                text=data["choices"][0]["message"]["content"],
                usage=data.get("usage")
            )