from models.schemas import ComparisonInput, ComparisonOutput, ComparisonTable
from services.llm_client import llm_client
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ComparisonAgent:
    """
    Structured product comparison.
    LLM used ONLY for narrative summary, NOT for schema alignment.
    """
    
    # Canonical attribute schema — covers all major product verticals.
    # The comparison agent uses whatever subset is passed in attributes_to_compare;
    # entries here only add formatting metadata (unit display, type).
    CANONICAL_ATTRIBUTES = {
        # ── Universal ──────────────────────────────────────────────────
        "price":             {"type": "numeric", "unit": "currency"},
        "rating":            {"type": "numeric", "unit": "stars"},
        "brand":             {"type": "text"},
        "category":          {"type": "text"},
        "color":             {"type": "text"},
        "weight":            {"type": "numeric", "unit": "kg"},
        "warranty":          {"type": "text"},
        # ── Electronics / computing ────────────────────────────────────
        "battery":           {"type": "numeric", "unit": "mAh"},
        "screen_size":       {"type": "numeric", "unit": "inches"},
        "storage":           {"type": "numeric", "unit": "GB"},
        "ram":               {"type": "numeric", "unit": "GB"},
        "processor":         {"type": "text"},
        "resolution":        {"type": "text"},
        "connectivity":      {"type": "text"},
        # ── Fashion / apparel ──────────────────────────────────────────
        "size":              {"type": "text"},
        "material":          {"type": "text"},
        "fit":               {"type": "text"},
        "gender":            {"type": "text"},
        # ── Furniture / home décor ─────────────────────────────────────
        "dimensions":        {"type": "text"},
        "weight_capacity":   {"type": "numeric", "unit": "kg"},
        "assembly_required": {"type": "text"},
        # ── Kitchen / home appliances ──────────────────────────────────
        "capacity":          {"type": "numeric", "unit": "L"},
        "power":             {"type": "numeric", "unit": "W"},
    }
    
    def __init__(self):
        pass
        
    async def compare(self, input: ComparisonInput, product_data: List[Dict[str, Any]]) -> ComparisonOutput:
        """
        Compare products across specified attributes.
        
        Args:
            input: Comparison request
            product_data: Full product data (fetched separately)
            
        Returns:
            Structured comparison table + narrative
        """
        logger.info(f"Comparing {len(input.product_ids)} products")
        
        # Step 1: Extract attributes (deterministic)
        table = self._build_comparison_table(
            product_data=product_data,
            attributes=input.attributes_to_compare
        )
        
        # Step 2: Generate narrative summary (LLM)
        narrative = await self._generate_narrative(table, product_data)
        
        return ComparisonOutput(
            comparison_table=table,
            narrative_summary=narrative,
            products_compared=input.product_ids
        )
        
    def _build_comparison_table(
        self,
        product_data: List[Dict[str, Any]],
        attributes: List[str]
    ) -> ComparisonTable:
        """
        Build structured comparison table.
        Pure deterministic logic - no LLM.
        """
        headers = ["Product"] + attributes
        rows = []
        
        for product in product_data:
            row = {
                "Product": product.get("name", product.get("product_id", "Unknown"))
            }
            
            for attr in attributes:
                # Extract from canonical schema
                if attr in self.CANONICAL_ATTRIBUTES:
                    value = product.get(attr, "N/A")
                    attr_schema = self.CANONICAL_ATTRIBUTES[attr]
                    
                    # Format with unit if applicable
                    if attr_schema.get("unit") and value != "N/A":
                        row[attr] = f"{value} {attr_schema['unit']}"
                    else:
                        row[attr] = value
                else:
                    # Fallback for custom attributes
                    row[attr] = product.get(attr, "N/A")
                    
            rows.append(row)
            
        return ComparisonTable(
            headers=headers,
            rows=rows
        )
        
    async def _generate_narrative(
        self,
        table: ComparisonTable,
        product_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate natural language comparison summary using LLM.
        """
        # Build context for LLM
        table_text = self._format_table_for_llm(table)
        
        system_prompt = """You are a product comparison assistant.
Given a comparison table, generate a brief 2-3 sentence summary highlighting:
1. Key differences
2. Best value option
3. Notable trade-offs

Be factual. Do NOT invent attributes not in the table."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Comparison table:\n{table_text}\n\nGenerate summary:"}
        ]
        
        try:
            result = await llm_client.chat_completion(
                messages=messages,
                temperature=0.3,  # Slightly creative but controlled
                max_tokens=150
            )
            return result["content"].strip()
            
        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return "Comparison table generated. See details above."
            
    def _format_table_for_llm(self, table: ComparisonTable) -> str:
        """
        Convert table to text format for LLM.
        """
        lines = [" | ".join(table.headers)]
        lines.append("-" * 50)
        
        for row in table.rows:
            line = " | ".join(str(row.get(h, "N/A")) for h in table.headers)
            lines.append(line)
            
        return "\n".join(lines)

# Global instance
comparison_agent = ComparisonAgent()