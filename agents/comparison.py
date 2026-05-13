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
        
        # Step 2: Generate narrative summary (deterministic — no LLM)
        narrative = self._build_narrative(table)
        
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
                "Product": product.get("name", product.get("product_id", "Unknown")).split("|")[0].strip()
            }
            
            for attr in attributes:
                if attr in self.CANONICAL_ATTRIBUTES:
                    value = product.get(attr, "N/A")
                    row[attr] = self._fmt_cell(attr, value, self.CANONICAL_ATTRIBUTES[attr])
                else:
                    row[attr] = product.get(attr, "N/A")
                    
            rows.append(row)
            
        return ComparisonTable(
            headers=headers,
            rows=rows
        )
        
    def _build_narrative(self, table: ComparisonTable) -> str:
        """
        Build a concise, deterministic narrative from the comparison table.
        Highlights the most affordable product, best-rated, and standout specs.
        No LLM — fast and reliable.
        """
        rows = table.rows
        attrs = table.headers[1:]   # skip the "Product" column
        if not rows:
            return ""

        highlights = []

        for attr in attrs:
            numeric_vals = []
            for row in rows:
                raw = row.get(attr, "N/A")
                if raw in ("N/A", None, ""):
                    continue
                try:
                    num = float(str(raw).split()[0].replace(",", ""))
                    numeric_vals.append((row["Product"], num, raw))
                except (ValueError, TypeError):
                    pass

            if len(numeric_vals) < 2:
                continue

            if attr == "price":
                best = min(numeric_vals, key=lambda x: x[1])
                highlights.append(f"{best[0]} is the most affordable ({self._fmt_value('price', best[1], best[2])})")
            elif attr == "rating":
                best = max(numeric_vals, key=lambda x: x[1])
                highlights.append(f"{best[0]} has the highest rating ({self._fmt_value('rating', best[1], best[2])})")
            elif attr == "ram":
                best = max(numeric_vals, key=lambda x: x[1])
                highlights.append(f"{best[0]} has the most RAM ({self._fmt_value('ram', best[1], best[2])})")
            elif attr == "storage":
                best = max(numeric_vals, key=lambda x: x[1])
                highlights.append(f"{best[0]} offers the most storage ({self._fmt_value('storage', best[1], best[2])})")

        if not highlights:
            names = [r["Product"] for r in rows]
            return "Comparing " + " vs ".join(names) + "."

        return "  ·  ".join(highlights) + "."

    @staticmethod
    def _fmt_cell(attr: str, value, schema: dict) -> str:
        """Format a cell value for display in the comparison table."""
        if value is None or value == "N/A" or value == "":
            return "N/A"
        unit = schema.get("unit", "")
        if not unit:
            return str(value)
        if unit == "currency":
            try:
                return f"Rs. {int(float(value)):,}"
            except (ValueError, TypeError):
                return str(value)
        elif unit == "stars":
            return f"{value} / 5"
        else:
            return f"{value} {unit}"

    @staticmethod
    def _fmt_value(attr: str, num: float, raw: str) -> str:
        """Format a numeric value for display in the narrative."""
        if attr == "price":
            return f"Rs. {int(num):,}"
        elif attr == "rating":
            return f"{num} / 5"
        return str(raw)

    async def _generate_narrative(
        self,
        table: ComparisonTable,
        product_data: List[Dict[str, Any]]
    ) -> str:
        """
        Legacy LLM-based narrative — kept for reference but no longer called.
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