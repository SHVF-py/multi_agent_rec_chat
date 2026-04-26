"""
FakeStore API → Quiribot Ingestion Script
==========================================

Fetches all products from https://fakestoreapi.com/products, generates
text embeddings via the embedding service, and upserts them into the vector
DB so the multi-agent pipeline can search and rank them.

After indexing it also builds same-category and cross-category association
rules and writes them to data/association_rules.json so the MBA agent has
real data to work with.

Usage
-----
    # From the project root:
    python data/ingest_fakestore.py

    # Optional: specify a tenant namespace
    python data/ingest_fakestore.py --tenant-id my_store

The script is idempotent — re-running it will overwrite existing entries
for the same product_id / tenant_id combination (upsert semantics).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

# ---------------------------------------------------------------------------
# Ensure the project root is importable when running as a script
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings          # noqa: E402
from services.embedding_client import embedding_client  # noqa: E402
from services.vector_client import vector_client        # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_fakestore")

# ---------------------------------------------------------------------------
# FakeStore → system schema mapping
# ---------------------------------------------------------------------------

# FakeStore uses a misspelled "jewelery"; map to a clean canonical form.
# All other categories are left as-is so they remain searchable and
# no bias is introduced in the agent layer.
_CATEGORY_MAP: Dict[str, str] = {
    "jewelery":         "jewellery",        # fix FakeStore typo only
    "electronics":      "electronics",
    "men's clothing":   "men's clothing",
    "women's clothing": "women's clothing",
}


def _map_product(raw: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """
    Convert a raw FakeStore product dict into the system's metadata schema.

    FakeStore shape:
        {id, title, price, description, category, image, rating:{rate, count}}

    System metadata shape (matches what retrieval/ranking agents expect):
        product_id, name, price, category, brand,
        rating, stock_quantity, description, image,
        in_stock, source_type, timestamp, tenant_id
    """
    rating_obj = raw.get("rating", {})
    category_raw = raw.get("category", "").lower()

    return {
        "product_id":     str(raw["id"]),
        "name":           raw["title"],
        "price":          float(raw["price"]),
        "category":       _CATEGORY_MAP.get(category_raw, category_raw),
        # FakeStore has no brand field; store as generic so the ranking agent
        # doesn't penalise these products when no brand constraint is set.
        "brand":          "Unbranded",
        "rating":         float(rating_obj.get("rate", 0.0)),
        # Use rating.count as a proxy for popularity / stock depth.
        "stock_quantity": int(rating_obj.get("count", 50)),
        "description":    raw.get("description", ""),
        "image":          raw.get("image", ""),
        "in_stock":       True,
        # source_type tells the retrieval agent what kind of content was embedded.
        "source_type":    "description",
        "timestamp":      "2024-01-01T00:00:00",
        "tenant_id":      tenant_id,
    }


def _build_embed_text(raw: Dict[str, Any]) -> str:
    """
    Construct the text that gets embedded for each product.

    Combining title + description gives the embedding model enough context
    to distinguish products across different categories.
    """
    title = raw.get("title", "")
    desc  = raw.get("description", "")
    category = raw.get("category", "")
    return f"{title}. Category: {category}. {desc}"


# ---------------------------------------------------------------------------
# Association rule generation
# ---------------------------------------------------------------------------

def _build_association_rules(
    raw_products: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build MBA association rules from FakeStore products.

    Strategy:
    - Same-category: every product A recommends every other product B in the
      same category.  Confidence = B.rating.rate / 5  (higher-rated items are
      more likely to satisfy the shopper).
    - Complementary cross-category: jewellery ↔ clothing (bidirectional), with
      a slightly lower confidence multiplier to reflect they are suggestions,
      not guaranteed pairings.

    The rules use FakeStore's raw category strings (all lowercase) internally
    so this function has zero dependency on the system's normalisation layer.
    """
    # Group by raw FakeStore category string
    by_category: Dict[str, List[Dict]] = {}
    for p in raw_products:
        cat = p.get("category", "").lower()
        by_category.setdefault(cat, []).append(p)

    # Category pairs that naturally cross-sell (bidirectional)
    CROSS_PAIRS = [
        ("men's clothing",   "jewelery"),
        ("women's clothing", "jewelery"),
    ]

    rules: Dict[str, List[Dict]] = {}

    for product in raw_products:
        pid = str(product["id"])
        cat = product.get("category", "").lower()
        product_rules: List[Dict] = []

        # ── Same-category rules ──────────────────────────────────────────────
        for other in by_category.get(cat, []):
            if str(other["id"]) == pid:
                continue
            other_rate = float(other.get("rating", {}).get("rate", 0.0))
            conf = round(min(other_rate / 5.0, 1.0), 2)
            sup  = round(conf * 0.20, 3)
            product_rules.append({
                "consequent": str(other["id"]),
                "confidence": conf,
                "support":    sup,
                "rule_type":  "frequently_bought_together",
            })

        # ── Cross-category complement rules ──────────────────────────────────
        for (cat_a, cat_b) in CROSS_PAIRS:
            complement = None
            if cat == cat_a:
                complement = cat_b
            elif cat == cat_b:
                complement = cat_a

            if complement:
                for other in by_category.get(complement, []):
                    other_rate = float(other.get("rating", {}).get("rate", 0.0))
                    conf = round(min(other_rate / 5.0 * 0.75, 1.0), 2)
                    sup  = round(conf * 0.12, 3)
                    product_rules.append({
                        "consequent": str(other["id"]),
                        "confidence": conf,
                        "support":    sup,
                        "rule_type":  "complementary_item",
                    })

        # Highest confidence first
        product_rules.sort(key=lambda x: x["confidence"], reverse=True)
        rules[pid] = product_rules

    return rules


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def _fetch_products(api_url: str) -> List[Dict[str, Any]]:
    """Fetch all products from FakeStore API (synchronous)."""
    endpoint = f"{api_url.rstrip('/')}/products"
    logger.info(f"Fetching products from {endpoint} …")
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(endpoint)
            response.raise_for_status()
        products: List[Dict[str, Any]] = response.json()
        logger.info(f"Received {len(products)} products.")
        return products
    except httpx.HTTPError as exc:
        logger.error(f"Failed to fetch products: {exc}")
        raise


# ---------------------------------------------------------------------------
# Main async ingestion pipeline
# ---------------------------------------------------------------------------

async def ingest(tenant_id: str) -> None:
    api_url = settings.FAKESTORE_API_URL
    raw_products = _fetch_products(api_url)

    total   = len(raw_products)
    success = 0

    for i, raw in enumerate(raw_products, start=1):
        meta = _map_product(raw, tenant_id)
        embed_text = _build_embed_text(raw)

        try:
            vector = await embedding_client.embed_text(embed_text)
            await vector_client.upsert(
                product_id=meta["product_id"],
                vector=vector,
                metadata=meta,
                tenant_id=tenant_id,
            )
            logger.info(
                f"[{i:>2}/{total}] ✓ Indexed  id={meta['product_id']:>3}"
                f"  cat={meta['category']:<20}  {meta['name'][:50]}"
            )
            success += 1

        except Exception as exc:
            logger.error(
                f"[{i:>2}/{total}] ✗ Failed   id={meta['product_id']}  — {exc}"
            )

    logger.info(f"Indexing complete: {success}/{total} products upserted.")

    # ── Build and persist MBA association rules ──────────────────────────────
    logger.info("Building association rules …")
    rules = _build_association_rules(raw_products)

    rules_path = Path(__file__).resolve().parent / "association_rules.json"
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2)

    total_rules = sum(len(v) for v in rules.values())
    logger.info(
        f"Association rules written → {rules_path} "
        f"({len(rules)} products, {total_rules} rules total)"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest FakeStore API products into the Quiribot vector DB."
    )
    parser.add_argument(
        "--tenant-id",
        default="default",
        help="Tenant namespace for multi-tenant isolation (default: 'default')",
    )
    args = parser.parse_args()
    asyncio.run(ingest(tenant_id=args.tenant_id))


if __name__ == "__main__":
    main()
