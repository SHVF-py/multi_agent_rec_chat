from models.schemas import RankingInput, RankingOutput, RankedProduct, ScoringBreakdown, RetrievalResult
from config.settings import settings
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RankingAgent:
    """
    Deterministic product ranking using weighted scoring.
    NO LLM INVOLVEMENT.
    """
    
    def __init__(self):
        # Default weights from config
        self.default_weights = {
            "relevance": settings.WEIGHT_RELEVANCE,
            "constraints": settings.WEIGHT_CONSTRAINTS,
            "rating": settings.WEIGHT_RATING,
            "personalization": settings.WEIGHT_PERSONALIZATION,
            "stock": settings.WEIGHT_STOCK
        }
        
    def rank(self, input: RankingInput) -> RankingOutput:
        """
        Main ranking method.
        
        Formula:
        final_score = w1*relevance + w2*constraints + w3*rating + w4*personalization + w5*stock
        
        All component scores normalized to [0, 1].
        """
        logger.info(f"Ranking {len(input.retrieval_results)} products")
        
        # Use provided weights or default
        weights = input.weights if input.weights else self.default_weights
        
        # Score each product
        scored_products = []
        for result in input.retrieval_results:
            breakdown = self._compute_score(
                result=result,
                user_features=input.user_features,
                constraints=input.constraints,
                weights=weights
            )
            
            scored_products.append({
                "product_id": result.product_id,
                "breakdown": breakdown,
                "metadata": result.metadata
            })
            
        # Sort by final score descending
        scored_products.sort(key=lambda x: x["breakdown"].final_score, reverse=True)
        
        # Assign ranks
        ranked = []
        for rank, item in enumerate(scored_products, start=1):
            ranked.append(RankedProduct(
                product_id=item["product_id"],
                rank=rank,
                scoring=item["breakdown"],
                metadata=item["metadata"]
            ))

        if ranked:
            logger.info(f"Ranking complete. Top score: {ranked[0].scoring.final_score:.4f}")
        else:
            logger.warning("Ranking complete. No products to rank.")
        
        return RankingOutput(
            ranked_products=ranked,
            weights_used=weights
        )
        
    def _compute_score(
        self,
        result: RetrievalResult,
        user_features: Dict[str, Any],
        constraints: Dict[str, Any],
        weights: Dict[str, float]
    ) -> ScoringBreakdown:
        """
        Compute component scores and aggregate.
        """
        # 1. Relevance score (from vector similarity)
        relevance_score = result.similarity_score  # Already [0, 1]
        
        # 2. Constraint match score
        constraint_match = self._compute_constraint_match(result.metadata, constraints)
        
        # 3. Rating score (normalize ratings to [0, 1])
        rating = result.metadata.get("rating", 0.0)
        max_rating = 5.0
        rating_score = rating / max_rating if rating > 0 else 0.0
        
        # 4. Personalization score
        personalization_score = self._compute_personalization(result, user_features)
        
        # 5. Stock priority score
        stock_qty = result.metadata.get("stock_quantity", 0)
        stock_score = min(stock_qty / 100.0, 1.0) if stock_qty > 0 else 0.0
        
        # Aggregate
        final_score = (
            weights["relevance"] * relevance_score +
            weights["constraints"] * constraint_match +
            weights["rating"] * rating_score +
            weights["personalization"] * personalization_score +
            weights["stock"] * stock_score
        )
        
        return ScoringBreakdown(
            relevance_score=relevance_score,
            constraint_match_score=constraint_match,
            rating_score=rating_score,
            personalization_score=personalization_score,
            stock_priority_score=stock_score,
            final_score=final_score
        )
        
    def _compute_constraint_match(self, metadata: Dict[str, Any], constraints: Dict[str, Any]) -> float:
        """
        Evaluate actual constraint values against product metadata.
        Returns fraction of constraints satisfied (0.0 – 1.0).
        """
        if not constraints:
            return 1.0  # No constraints = full match

        checks = 0
        matched = 0

        # Price range check
        if "price_range" in constraints:
            pr = constraints["price_range"]
            product_price = metadata.get("price", None)
            if product_price is not None:
                checks += 1
                lo = pr.get("min", 0)
                hi = pr.get("max", float("inf"))
                if lo <= float(product_price) <= hi:
                    matched += 1

        # Brand check (case-insensitive)
        if "brand" in constraints:
            product_brand = metadata.get("brand", "")
            checks += 1
            if product_brand.lower() == constraints["brand"].lower():
                matched += 1

        # Category check (case-insensitive)
        if "category" in constraints:
            product_category = metadata.get("category", "")
            checks += 1
            if product_category.lower() == constraints["category"].lower():
                matched += 1

        # Size check (fashion / apparel)
        if "size" in constraints:
            product_size = metadata.get("size", "")
            checks += 1
            if str(product_size).lower() == str(constraints["size"]).lower():
                matched += 1

        # Color check (fashion / furniture / general)
        if "color" in constraints:
            product_color = metadata.get("color", "")
            checks += 1
            if product_color.lower() == constraints["color"].lower():
                matched += 1

        # Material check (fashion / furniture)
        if "material" in constraints:
            product_material = metadata.get("material", "")
            checks += 1
            if product_material.lower() == constraints["material"].lower():
                matched += 1

        return matched / checks if checks > 0 else 1.0
        
    def _compute_personalization(self, result: RetrievalResult, user_features: Dict[str, Any]) -> float:
        """
        Personalization based on user history and preferences.
        
        If no user history, return 0.0.
        """
        if not user_features or not user_features.get("history"):
            return 0.0
            
        # Simple implementation: check if product category matches user preferences
        user_preferred_categories = user_features.get("preferred_categories", [])
        product_category = result.metadata.get("category", "")
        
        if product_category in user_preferred_categories:
            return 1.0
            
        # Check brand preference
        user_preferred_brands = user_features.get("preferred_brands", [])
        product_brand = result.metadata.get("brand", "")
        
        if product_brand in user_preferred_brands:
            return 0.8
            
        return 0.0

# Global instance
ranking_agent = RankingAgent()