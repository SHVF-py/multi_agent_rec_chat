import httpx
from typing import List, Dict, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class VectorClient:
    """
    Client for FAISS-backed vector search API on host.
    """

    # Prevents ngrok from serving its browser-warning interstitial page
    # when the service is reachable via an ngrok tunnel.
    _NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}
    
    def __init__(self):
        self.base_url = settings.HOST_VECTOR_URL
        self.timeout = settings.VECTOR_TIMEOUT
        self.api_key = settings.HOST_API_KEY
        
    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any],
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Search vector database with metadata filtering.
        
        Args:
            query_vector: Query embedding
            top_k: Number of results
            filters: Metadata filters (price, category, stock, etc.)
            tenant_id: Multi-tenant isolation
            
        Returns:
            List of search results with scores
        """
        headers = {
            "Content-Type": "application/json",
            **self._NGROK_HEADERS,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Ensure tenant_id is always in filters
        filters["tenant_id"] = tenant_id
        
        payload = {
            "vector": query_vector,
            "top_k": top_k,
            "filters": filters
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                results = data["results"]
                
                logger.info(f"Vector search returned {len(results)} results")
                return results
                
            except httpx.TimeoutException as e:
                logger.error(f"Vector search timeout: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"Vector search HTTP error: {e.response.status_code}")
                raise

    async def upsert(
        self,
        product_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        tenant_id: str
    ) -> bool:
        """
        Insert or update a single product in the vector database.

        Args:
            product_id: Unique product identifier
            vector:     Embedding vector for the product
            metadata:   Structured product metadata stored alongside the vector
            tenant_id:  Multi-tenant namespace

        Returns:
            True on success, raises on failure
        """
        headers = {
            "Content-Type": "application/json",
            **self._NGROK_HEADERS,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "product_id": product_id,
            "vector": vector,
            "metadata": {**metadata, "tenant_id": tenant_id},
            "tenant_id": tenant_id,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/upsert",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                logger.debug(f"Upserted product {product_id} into tenant '{tenant_id}'")
                return True

            except httpx.TimeoutException as e:
                logger.error(f"Vector upsert timeout for product {product_id}: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Vector upsert HTTP error for product {product_id}: "
                    f"{e.response.status_code}"
                )
                raise

# Global instance
vector_client = VectorClient()