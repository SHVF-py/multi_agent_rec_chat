import httpx
from typing import Dict, Any, List, Optional
from config.settings import settings
import json
import re
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Client for Phi-3 model via vLLM OpenAI-compatible API.
    """

    # Prevents ngrok from serving its browser-warning interstitial page
    # when the service is reachable via an ngrok tunnel.
    _NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}
    
    def __init__(self):
        self.base_url = settings.HOST_LLM_URL
        self.timeout = settings.LLM_TIMEOUT
        self.api_key = settings.HOST_API_KEY
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 512,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Call Phi-3 chat completion endpoint.
        
        Args:
            messages: OpenAI format messages
            temperature: 0.0 for deterministic (intent extraction), higher for creative
            max_tokens: Response length limit
            response_format: {"type": "json_object"} to force JSON
            
        Returns:
            Parsed response dict
            
        Raises:
            httpx.TimeoutException: Request timed out
            ValueError: Invalid response format
        """
        headers = {
            "Content-Type": "application/json",
            **self._NGROK_HEADERS,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/llm/chat",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                content = data["text"]
                
                logger.info(f"LLM call successful. Tokens: {data.get('usage', {})}")
                
                return {
                    "content": content,
                    "usage": data.get("usage", {}),
                    "finish_reason": None
                }
                
            except httpx.TimeoutException as e:
                logger.error(f"LLM timeout: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
                raise
            except (KeyError, IndexError) as e:
                logger.error(f"LLM response parse error: {e}")
                raise ValueError("Invalid LLM response structure")
                
    async def extract_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512
    ) -> Dict[str, Any]:
        """
        Helper to get JSON response from LLM.
        """
        result = await self.chat_completion(
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        content = result["content"].strip()
        
        # Remove markdown code fences if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Last resort: find the first {...} block anywhere in the text
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"JSON parse error — could not extract JSON from:\n{content}")
        raise ValueError(f"LLM returned invalid JSON")

# Global instance
llm_client = LLMClient()