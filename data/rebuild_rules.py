"""
MBA Rule Regeneration Script
==============================
Rebuilds ``data/association_rules.json`` from the existing indexed products
stored in ``data/faiss_metadata.json``.

Run this whenever the product catalogue changes (e.g. after re-ingesting
new products) to keep the MBA agent's rules up-to-date without having to
re-embed or re-ingest everything.

Usage
-----
    # From the project root:
    python data/rebuild_rules.py

    # Specify custom paths if needed:
    python data/rebuild_rules.py --metadata data/faiss_metadata.json \\
                                  --output   data/association_rules.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rebuild_rules")

# ---------------------------------------------------------------------------
# Rule-building logic (works with the system metadata schema, not raw FakeStore)
# ---------------------------------------------------------------------------

# Category pairs that naturally cross-sell (bidirectional).
# Uses the normalised category strings stored in faiss_metadata.json.
_CROSS_PAIRS: List[tuple] = [
    ("men's clothing", "jewellery"),
    ("women's clothing", "jewellery"),
]


def build_rules_from_metadata(
    products: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build MBA association rules from system-schema product metadata.

    Strategy
    --------
    Same-category rules
        Every product A recommends every other product B in the same category.
        confidence = B.rating / 5  (higher-rated items are a safer suggestion).
        support    = confidence × 0.20

    Cross-category complement rules
        Clothing ↔ jewellery pairs, with a 0.75 confidence multiplier to signal
        they are suggestions rather than guaranteed pairings.
        support    = confidence × 0.12

    Rules are sorted by confidence (descending) per antecedent product.
    """
    # Group products by category
    by_category: Dict[str, List[Dict]] = {}
    for p in products:
        cat = p.get("category", "").lower()
        by_category.setdefault(cat, []).append(p)

    rules: Dict[str, List[Dict]] = {}

    for product in products:
        pid = str(product.get("product_id", product.get("id", "")))
        cat = product.get("category", "").lower()
        product_rules: List[Dict] = []

        # ── Same-category rules ──────────────────────────────────────────
        for other in by_category.get(cat, []):
            other_pid = str(other.get("product_id", other.get("id", "")))
            if other_pid == pid:
                continue
            other_rating = float(other.get("rating", 0.0))
            conf = round(min(other_rating / 5.0, 1.0), 2)
            sup = round(conf * 0.20, 3)
            product_rules.append(
                {
                    "consequent": other_pid,
                    "confidence": conf,
                    "support": sup,
                    "rule_type": "frequently_bought_together",
                }
            )

        # ── Cross-category complement rules ──────────────────────────────
        for cat_a, cat_b in _CROSS_PAIRS:
            complement = None
            if cat == cat_a:
                complement = cat_b
            elif cat == cat_b:
                complement = cat_a

            if complement:
                for other in by_category.get(complement, []):
                    other_pid = str(other.get("product_id", other.get("id", "")))
                    other_rating = float(other.get("rating", 0.0))
                    conf = round(min(other_rating / 5.0 * 0.75, 1.0), 2)
                    sup = round(conf * 0.12, 3)
                    product_rules.append(
                        {
                            "consequent": other_pid,
                            "confidence": conf,
                            "support": sup,
                            "rule_type": "complementary_item",
                        }
                    )

        # Sort highest confidence first
        product_rules.sort(key=lambda x: x["confidence"], reverse=True)
        rules[pid] = product_rules

    return rules


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_metadata(path: Path) -> List[Dict[str, Any]]:
    """Load all product metadata from the FAISS metadata JSON file."""
    if not path.exists():
        logger.error(f"Metadata file not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # faiss_metadata.json is a list of metadata dicts
    if not isinstance(data, list):
        logger.error("Expected faiss_metadata.json to be a JSON array.")
        sys.exit(1)

    logger.info(f"Loaded {len(data)} product entries from {path}")
    return data


def save_rules(rules: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    """Write association rules to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)

    total_rules = sum(len(v) for v in rules.values())
    logger.info(
        f"Association rules written → {path} "
        f"({len(rules)} antecedents, {total_rules} rules total)"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild MBA association rules from existing indexed product metadata. "
            "Run after adding or removing products to keep cross-sell suggestions fresh."
        )
    )
    parser.add_argument(
        "--metadata",
        default="data/faiss_metadata.json",
        help="Path to faiss_metadata.json (default: data/faiss_metadata.json)",
    )
    parser.add_argument(
        "--output",
        default="data/association_rules.json",
        help="Output path for association_rules.json (default: data/association_rules.json)",
    )
    args = parser.parse_args()

    metadata_path = Path(args.metadata)
    output_path = Path(args.output)

    # Load existing indexed products
    products = load_metadata(metadata_path)

    if not products:
        logger.warning("No products found in metadata file — nothing to do.")
        return

    # Log a category breakdown so it's easy to spot catalogue issues
    from collections import Counter
    cat_counts = Counter(p.get("category", "unknown") for p in products)
    logger.info("Category breakdown: " + ", ".join(f"{c}={n}" for c, n in cat_counts.most_common()))

    # Build rules
    logger.info("Building association rules …")
    rules = build_rules_from_metadata(products)

    # Persist
    save_rules(rules, output_path)
    logger.info("Done.")


if __name__ == "__main__":
    main()
