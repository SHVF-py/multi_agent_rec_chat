from models.schemas import ExplainabilityInput, ExplainabilityOutput, Explanation, RankedProduct
from services.llm_client import llm_client
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExplainabilityAgent:
    """
    Generates natural language explanations for recommendations.
    Must cite sources and timestamps.
    """
    
    SYSTEM_PROMPT = """You are Quiribot, a friendly shopping assistant having a natural conversation.

When recommending a product, write 1-2 warm, natural sentences explaining why it's a good pick.
Speak directly to the user. Reference the product name, its rating, and why it fits their query.
Do NOT use bullet points, scores, or technical jargon. Sound like a knowledgeable friend, not a report.

Example output:
"The Fjallraven Backpack is a great choice here — it's highly rated by over 500 shoppers and fits
comfortably within your budget at $109. It's perfect if you want something durable and stylish."
"""

    def __init__(self):
        pass
        
    async def explain(self, input: ExplainabilityInput) -> ExplainabilityOutput:
        """
        Generate explanations for top-N products.
        """
        logger.info(f"Generating explanations for top {input.top_n} products")
        
        explanations = []
        
        for product in input.ranked_products[:input.top_n]:
            explanation = await self._explain_product(
                product=product,
                query_context=input.query_context,
                evidence=input.evidence_sources
            )
            explanations.append(explanation)
            
        return ExplainabilityOutput(explanations=explanations)
        
    async def _explain_product(
        self,
        product: RankedProduct,
        query_context: str,
        evidence: List[Dict[str, Any]]
    ) -> Explanation:
        """
        Generate explanation for single product.
        """
        # Find evidence for this product
        product_evidence = [
            e for e in evidence 
            if e.get("product_id") == product.product_id
        ]
        
        # Build context for LLM
        context = self._build_explanation_context(
            product=product,
            query_context=query_context,
            evidence=product_evidence
        )
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": context}
        ]
        
        try:
            result = await llm_client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            summary = result["content"].strip()
            
            # Extract reasons and citations
            reasons = self._extract_reasons(product)
            citations = self._extract_citations(product_evidence)
            
            return Explanation(
                product_id=product.product_id,
                summary=summary,
                reasons=reasons,
                citations=citations
            )
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return Explanation(
                product_id=product.product_id,
                summary="This product was recommended based on relevance and ratings.",
                reasons=["High relevance score", "Good user rating"],
                citations=[]
            )
            
    def _build_explanation_context(
        self,
        product: RankedProduct,
        query_context: str,
        evidence: List[Dict[str, Any]]
    ) -> str:
        """
        Build context text for LLM.
        """
        lines = [
            f"User query: {query_context}",
            f"Product name: {product.metadata.get('name', product.product_id)}",
            f"Category: {product.metadata.get('category', 'N/A')}",
            f"Price: ${product.metadata.get('price', 'N/A')}",
            f"Rating: {product.metadata.get('rating', 'N/A')}/5",
            f"Rank: #{product.rank} out of results",
            f"Relevance score: {product.scoring.relevance_score:.2f}",
        ]
        
        return "\n".join(lines)
        
    def _extract_reasons(self, product: RankedProduct) -> List[str]:
        """
        Extract key reasons from scoring breakdown.
        """
        reasons = []
        
        if product.scoring.relevance_score > 0.7:
            reasons.append("High relevance to your query")
            
        if product.scoring.rating_score > 0.8:
            reasons.append("Excellent user ratings")
            
        if product.scoring.constraint_match_score == 1.0:
            reasons.append("Matches all your constraints")
            
        if product.scoring.personalization_score > 0.5:
            reasons.append("Aligned with your preferences")
            
        return reasons if reasons else ["Good overall score"]
        
    def _extract_citations(self, evidence: List[Dict[str, Any]]) -> List[str]:
        """
        Build citation references.
        """
        citations = []
        
        for e in evidence:
            source_id = e.get("source_id", "unknown")
            timestamp = e.get("timestamp", "")
            source_type = e.get("source_type", "")
            
            citation = f"{source_type}:{source_id}"
            if timestamp:
                citation += f" ({timestamp})"
                
            citations.append(citation)
            
        return citations

# Global instance
explainability_agent = ExplainabilityAgent()