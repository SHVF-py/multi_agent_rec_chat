import httpx
from typing import List, Union
from config.settings import settings
import logging
import base64

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """
    Client for text and image embedding APIs on host.
    """

    # Prevents ngrok from serving its browser-warning interstitial page
    # when the service is reachable via an ngrok tunnel.
    _NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}
    
    def __init__(self):
        self.base_url = settings.HOST_EMBEDDING_URL
        self.timeout = settings.EMBEDDING_TIMEOUT
        self.api_key = settings.HOST_API_KEY
        
    async def embed_text(self, text: str) -> List[float]:
        """
        Get text embedding vector.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector (list of floats)
        """
        headers = {
            "Content-Type": "application/json",
            **self._NGROK_HEADERS,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "input": text,
            "model": "bge-base"  # Adjust to actual model name
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embed",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = data["embedding"]
                
                logger.info(f"Text embedding generated. Dimension: {len(embedding)}")
                return embedding
                
            except httpx.TimeoutException as e:
                logger.error(f"Embedding timeout: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding HTTP error: {e.response.status_code}")
                raise
                
    async def embed_image(self, image_path: str) -> List[float]:
        """
        Get image embedding vector.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Embedding vector
        """
        headers = {
            "Content-Type": "application/json",
            **self._NGROK_HEADERS,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Read and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode()
            
        payload = {
            "image": image_b64,
            "model": "openclip"  # Adjust to actual model name
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embed",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = data["embedding"]
                
                logger.info(f"Image embedding generated. Dimension: {len(embedding)}")
                return embedding
                
            except httpx.TimeoutException as e:
                logger.error(f"Image embedding timeout: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"Image embedding HTTP error: {e.response.status_code}")
                raise

# Global instance
embedding_client = EmbeddingClient()