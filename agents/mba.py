from models.schemas import MBAInput, MBAOutput, CrossSellItem
from config.settings import settings
import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MBAAgent:
    """
    Market Basket Analysis for cross-sell recommendations.
    Uses pre-computed association rules (offline Apriori/FP-Growth).
    """
    
    def __init__(self):
        self.rules_path = settings.MBA_RULES_PATH
        self.min_confidence = settings.MBA_MIN_CONFIDENCE
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load pre-computed association rules from JSON file.
        
        Format:
        {
          "product_123": [
            {
              "consequent": "product_456",
              "confidence": 0.65,
              "support": 0.12,
              "rule_type": "frequently_bought_together"
            }
          ]
        }
        """
        try:
            with open(self.rules_path, 'r') as f:
                rules = json.load(f)
            logger.info(f"Loaded {len(rules)} product rule sets")
            return rules
        except FileNotFoundError:
            logger.warning(f"MBA rules file not found: {self.rules_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid MBA rules JSON: {e}")
            return {}
            
    def recommend(self, input: MBAInput) -> MBAOutput:
        """
        Get cross-sell recommendations for current product.
        
        Steps:
        1. Lookup rules for current product
        2. Filter by confidence threshold
        3. Check stock availability (if metadata available)
        4. Filter by user history compatibility
        5. Return top-N
        """
        logger.info(f"Getting cross-sell for product: {input.current_product_id}")
        
        # Get rules for this product
        product_rules = self.rules.get(input.current_product_id, [])
        
        if not product_rules:
            logger.info("No association rules found for this product")
            return MBAOutput(cross_sell_items=[], rules_applied=0)
            
        # Filter by confidence
        filtered_rules = [
            r for r in product_rules 
            if r.get("confidence", 0) >= self.min_confidence
        ]
        
        # Filter out products already in user history
        if input.user_history:
            filtered_rules = [
                r for r in filtered_rules
                if r.get("consequent") not in input.user_history
            ]
            
        # Convert to output schema
        cross_sell_items = []
        for rule in filtered_rules[:input.max_recommendations]:
            cross_sell_items.append(CrossSellItem(
                product_id=rule["consequent"],
                confidence=rule["confidence"],
                support=rule.get("support", 0.0),
                rule_type=rule.get("rule_type", "frequently_bought_together")
            ))
            
        logger.info(f"Returning {len(cross_sell_items)} cross-sell items")
        
        return MBAOutput(
            cross_sell_items=cross_sell_items,
            rules_applied=len(filtered_rules)
        )

# Global instance
mba_agent = MBAAgent()