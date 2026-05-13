from models.schemas import RetrievalInput, RetrievalOutput, RetrievalResult
from services.embedding_client import embedding_client
from services.vector_client import vector_client
from config.settings import settings
import logging
import time

logger = logging.getLogger(__name__)

class RetrievalAgent:
    """
    Performs vector search with strict metadata filtering.
    No ranking logic - just retrieval.
    """
    
    def __init__(self):
        self.default_top_k = settings.DEFAULT_TOP_K
        self.similarity_threshold = settings.RETRIEVAL_SIMILARITY_THRESHOLD
        
    async def retrieve(self, input: RetrievalInput) -> RetrievalOutput:
        """
        Main retrieval method.
        
        Steps:
        1. Get query embedding (if not provided)
        2. Build strict metadata filters
        3. Query vector DB
        4. Filter by similarity threshold
        5. Return results
        """
        start_time = time.time()
        logger.info(f"Retrieving products for query: {input.query_text[:50]}...")
        
        try:
            # Step 1: Get embedding
            if input.query_embedding is None:
                if input.image_path:
                    query_vector = await embedding_client.embed_image(input.image_path)
                else:
                    query_vector = await embedding_client.embed_text(input.query_text)
            else:
                query_vector = input.query_embedding
                
            # Step 2: Build filters
            filters = self._build_filters(input.filters)
            
            # Step 3: Vector search
            raw_results = await vector_client.search(
                query_vector=query_vector,
                top_k=input.top_k,
                filters=filters,
                tenant_id=input.tenant_id
            )
            
            # Step 4: Convert to schema and filter by threshold
            results = []
            for item in raw_results:
                score = item.get("similarity_score", 0.0)
                if score >= self.similarity_threshold:
                    results.append(RetrievalResult(
                        product_id=item["product_id"],
                        similarity_score=score,
                        source_type=item.get("source_type", "description"),
                        timestamp=item.get("timestamp", ""),
                        metadata=item.get("metadata", {})
                    ))
                    
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(f"Retrieved {len(results)} products in {retrieval_time:.2f}ms")
            
            return RetrievalOutput(
                results=results,
                total_candidates=len(raw_results),
                retrieval_time_ms=retrieval_time
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            # Return empty results on failure
            return RetrievalOutput(
                results=[],
                total_candidates=0,
                retrieval_time_ms=(time.time() - start_time) * 1000
            )
            
    def _build_filters(self, constraints: dict) -> dict:
        """
        Build metadata filters for the vector DB.

        ONLY hard numeric/boolean filters go here — things that must be
        exact matches and cannot be inferred semantically:
          - in_stock (boolean)
          - price_min / price_max (numeric)

        Category and brand are NOT passed as hard filters because:
          - FakeStore categories are multi-word ("men's clothing") and the LLM
            often extracts a different spelling/level ("jacket", "clothing").
          - All FakeStore products are "Unbranded" so any brand filter = 0 results.
        The ranking agent scores constraint matches separately.
        """
        filters: dict = {
            "in_stock": True  # always restrict to in-stock products
        }

        # Price range — only add finite bounds to avoid JSON float('inf') errors
        if "price_range" in constraints:
            pr = constraints["price_range"]
            if isinstance(pr, dict):
                lo = pr.get("min", 0)
                hi = pr.get("max", None)
                if lo and float(lo) > 0:
                    filters["price_min"] = float(lo)
                if hi is not None and hi != float("inf"):
                    filters["price_max"] = float(hi)

        return filters

# Global instance
retrieval_agent = RetrievalAgent()