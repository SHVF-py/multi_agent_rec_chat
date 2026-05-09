from models.schemas import QueryInput, QueryUnderstanding, IntentType
from services.llm_client import llm_client
from config.settings import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class QueryUnderstandingAgent:
    """
    Extracts intent and entities from user query using Phi-3.
    """
    
    SYSTEM_PROMPT = """You are a query understanding system for an e-commerce platform.
Extract the following from user queries:

1. Intent: search | recommendation | comparison | explanation | cross_sell
2. Constraints: price range, brand, category, features
3. Entities: product names, categories, attributes
4. Flags: requires_comparison, requires_cross_sell, requires_personalization

Return ONLY valid JSON matching this schema:
{
  "intent": "recommendation",
  "requires_comparison": false,
  "requires_cross_sell": true,
  "requires_personalization": true,
  "constraints": {
    "price_range": {"min": 500, "max": 1000},
    "brand": "Nike",
    "category": "footwear",
    "size": "42",
    "color": "black"
  },
  "entities": {
    "features": ["lightweight", "waterproof"]
  },
  "confidence": 0.87
}

Rules:
- This platform sells ALL product categories: electronics, fashion, furniture, appliances, kitchen, sports, beauty, and more.
- Extract constraints for any category: size/color/material for fashion; dimensions/material for furniture; storage/battery for electronics; capacity/power for appliances.
- Normalize brand names to proper case (nike -> Nike, samsung -> Samsung, ikea -> IKEA).
- Convert price to numeric.
- Confidence scoring: assign 0.8-1.0 for clear product queries (e.g. "best laptop", "show me shoes"), 0.5-0.7 for queries needing minor inference, 0.2-0.4 only for truly ambiguous or non-product queries with no intent.
"""

    def __init__(self):
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
        
    async def understand(self, input: QueryInput) -> QueryUnderstanding:
        """
        Main entry point for query understanding.
        """
        logger.info(f"Understanding query: {input.query_text}")
        
        # Build messages for LLM
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        # Inject prior turns so the agent can resolve references like
        # "what about in blue?" or "which one would you recommend?"
        for msg in (input.chat_history or [])[-6:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": f"Query: {input.query_text}"})
        
        try:
            # Call LLM with JSON mode
            result = await llm_client.extract_json(messages, max_tokens=512)
            
            # Validate and construct response
            understanding = QueryUnderstanding(
                intent=IntentType(result["intent"]),
                requires_comparison=result.get("requires_comparison", False),
                requires_cross_sell=result.get("requires_cross_sell", False),
                requires_personalization=result.get("requires_personalization", False),
                constraints=result.get("constraints", {}),
                entities=result.get("entities", {}),
                confidence=result.get("confidence", 0.5),
                raw_query=input.query_text
            )
            
            # Post-processing: normalize constraints
            understanding = self._normalize_constraints(understanding)

            # Strip infinite price bound — float('inf') can't be JSON-serialized
            pr = understanding.constraints.get("price_range")
            if isinstance(pr, dict) and pr.get("max") == float("inf"):
                pr.pop("max", None)

            # Merge preprocessing price hints as fallback
            if input.preprocessing and input.preprocessing.price_hints:
                self._merge_price_hints(understanding, input.preprocessing.price_hints)

            logger.info(f"Intent: {understanding.intent}, Confidence: {understanding.confidence}")

            return understanding
            
        except Exception as e:
            logger.error(f"Query understanding failed: {e}")
            # Keyword-based fallback so the orchestrator can still run
            raw = input.query_text.lower()
            if any(w in raw for w in ["compare", "vs", "versus", "difference", "better"]):
                fallback_intent = IntentType.COMPARISON
            elif any(w in raw for w in ["recommend", "best", "top", "suggest", "rated", "popular"]):
                fallback_intent = IntentType.RECOMMENDATION
            elif any(w in raw for w in ["why", "explain", "how", "what is"]):
                fallback_intent = IntentType.EXPLANATION
            else:
                fallback_intent = IntentType.SEARCH
            return QueryUnderstanding(
                intent=fallback_intent,
                confidence=0.5,   # enough to pass threshold and proceed
                raw_query=input.query_text,
                constraints={"in_stock": True},
                entities={}
            )
            
    def _normalize_constraints(self, understanding: QueryUnderstanding) -> QueryUnderstanding:
        """
        Post-process constraints to ensure consistency.
        """
        constraints = understanding.constraints
        
        # Ensure price range is numeric
        if "price_range" in constraints:
            pr = constraints["price_range"]
            if isinstance(pr, dict):
                pr["min"] = float(pr.get("min", 0))
                pr["max"] = float(pr.get("max", float('inf')))
                
        # Ensure in_stock is boolean
        if "in_stock" in constraints:
            constraints["in_stock"] = bool(constraints["in_stock"])
        else:
            constraints["in_stock"] = True  # Default to in-stock only
            
        # Normalize brand to title case
        if "brand" in constraints:
            constraints["brand"] = constraints["brand"].title()
            
        understanding.constraints = constraints
        return understanding

    def _merge_price_hints(
        self, understanding: QueryUnderstanding, price_hints: dict
    ) -> None:
        """
        Merge regex-extracted price hints into constraints when the LLM did
        not already populate a price_range. Acts as a fallback only — the
        LLM's output is never overwritten.
        """
        if "price_range" not in understanding.constraints:
            pr: dict = {}
            if "min_price" in price_hints:
                pr["min"] = float(price_hints["min_price"])
            if "max_price" in price_hints:
                pr["max"] = float(price_hints["max_price"])
            if pr:
                understanding.constraints["price_range"] = pr
                logger.debug(f"Injected preprocessing price hints: {pr}")

# Global instance
query_understanding_agent = QueryUnderstandingAgent()