"""
Unified product ingestion pipeline — platform-agnostic.
Replaces data/ingest_fakestore.py.

Usage
-----
    # Auto-detect platform:
    python data/ingest.py --url https://mystore.com --tenant-id mystore

    # Explicit WooCommerce:
    python data/ingest.py --url https://mystore.com --platform woocommerce \
        --consumer-key ck_xxx --consumer-secret cs_xxx --tenant-id mystore

    # Explicit Shopify:
    python data/ingest.py --url https://mystore.myshopify.com \
        --platform shopify --storefront-token shpat_xxx --tenant-id mystore

    # Force scraper:
    python data/ingest.py --url https://mystore.com --platform scraper \
        --tenant-id mystore

Can also be called programmatically from the portal's sync endpoint.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from data.connectors.base import ProductMetadata
from data.connectors.woocommerce import WooCommerceConnector
from data.connectors.shopify import ShopifyConnector
from data.connectors.scraper import ScraperConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")

# ---------------------------------------------------------------------------
# Association rule builder (same cross-sell logic as before, now generic)
# ---------------------------------------------------------------------------

_CROSS_CATEGORY_PAIRS = [
    ("men's clothing",   "jewellery"),
    ("women's clothing", "jewellery"),
    ("electronics",      "men's clothing"),
]


def _build_association_rules(products: List[ProductMetadata]) -> Dict[str, List[Dict]]:
    from collections import defaultdict

    by_category: Dict[str, List[str]] = defaultdict(list)
    for p in products:
        by_category[p.category.lower()].append(p.product_id)

    rules: Dict[str, List[Dict]] = {}

    # Same-category rules
    for cat, pids in by_category.items():
        if len(pids) < 2:
            continue
        for pid in pids:
            peers = [x for x in pids if x != pid][:4]
            rules[pid] = [{"product_id": peer, "confidence": 0.7} for peer in peers]

    # Cross-category rules
    for cat_a, cat_b in _CROSS_CATEGORY_PAIRS:
        pids_a = by_category.get(cat_a, [])
        pids_b = by_category.get(cat_b, [])
        if not pids_a or not pids_b:
            continue
        for pid in pids_a:
            existing = rules.get(pid, [])
            cross = [{"product_id": p, "confidence": 0.5} for p in pids_b[:2]]
            rules[pid] = existing + cross

    return rules


# ---------------------------------------------------------------------------
# Platform auto-detection (with HTTP probe)
# ---------------------------------------------------------------------------

async def _detect_platform(site_url: str) -> str:
    """
    Probe the site to detect its platform:
    1. Check for WooCommerce REST API endpoint
    2. Check for Shopify meta tag
    3. Fall back to scraper
    """
    base = site_url.rstrip("/")
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # WooCommerce probe
        try:
            resp = await client.get(f"{base}/wp-json/wc/v3/products?per_page=1")
            if resp.status_code in (200, 401, 403):
                logger.info("Detected platform: woocommerce")
                return "woocommerce"
        except Exception:
            pass

        # Shopify probe
        try:
            resp = await client.get(base)
            if "myshopify.com" in resp.url.host or "Shopify" in resp.headers.get("X-Shopify-Stage", ""):
                logger.info("Detected platform: shopify")
                return "shopify"
            if "cdn.shopify.com" in resp.text or "Shopify.theme" in resp.text:
                logger.info("Detected platform: shopify")
                return "shopify"
        except Exception:
            pass

    logger.info("Platform detection inconclusive — using scraper")
    return "scraper"


# ---------------------------------------------------------------------------
# Main ingestion function (called by portal sync endpoint + CLI)
# ---------------------------------------------------------------------------

async def run_ingestion(
    site_url: str,
    tenant_id: str,
    platform: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    gateway_url: str = "http://localhost:9000",
) -> int:
    """
    Full ingestion pipeline:
      1. Pick connector
      2. Fetch products
      3. Embed + upsert into FAISS via gateway
      4. Build & save association rules
      Returns number of products successfully indexed.
    """
    creds = credentials or {}

    if not platform or platform == "auto":
        platform = await _detect_platform(site_url)

    # Build connector
    if platform == "woocommerce":
        connector = WooCommerceConnector(
            base_url       = site_url,
            consumer_key   = creds.get("consumer_key", ""),
            consumer_secret= creds.get("consumer_secret", ""),
        )
    elif platform == "shopify":
        connector = ShopifyConnector(
            shop_domain      = site_url,
            storefront_token = creds.get("storefront_token", ""),
        )
    elif platform in ("json_upload", "csv_upload"):
        from data.connectors.csv_json import CsvJsonConnector
        connector = CsvJsonConnector(creds.get("upload_path", ""))
    else:
        connector = ScraperConnector(site_url)

    logger.info(f"Fetching products from {site_url} via {platform} ...")
    products = await connector.fetch_products()
    logger.info(f"Fetched {len(products)} products.")

    if not products:
        logger.warning("No products returned — nothing to index.")
        return 0

    # Embed + upsert via gateway
    indexed = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for p in products:
            embed_text = p.to_embed_text()
            meta       = p.to_metadata_dict(tenant_id)

            # Get embedding
            try:
                embed_resp = await client.post(
                    f"{gateway_url}/embed/text",
                    json={"text": embed_text},
                )
                embed_resp.raise_for_status()
                vector = embed_resp.json()["vector"]
            except Exception as exc:
                logger.error(f"Embedding failed for '{p.name}': {exc}")
                continue

            # Upsert into FAISS
            try:
                upsert_resp = await client.post(
                    f"{gateway_url}/vector/text/add",
                    json={"vectors": [vector], "metadata": [meta]},
                )
                upsert_resp.raise_for_status()
                indexed += 1
            except Exception as exc:
                logger.error(f"Upsert failed for '{p.name}': {exc}")

    logger.info(f"Indexed {indexed}/{len(products)} products into FAISS.")

    # Save association rules
    rules_path = Path(settings.MBA_RULES_PATH)
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules = _build_association_rules(products)
    with rules_path.open("w") as f:
        json.dump(rules, f, indent=2)
    logger.info(f"Saved {len(rules)} association rules to {rules_path}.")

    return indexed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Quiribot product ingestion pipeline")
    p.add_argument("--url",              required=True, help="Store URL")
    p.add_argument("--tenant-id",        required=True, help="Tenant namespace")
    p.add_argument("--platform",         default="auto",
                   choices=["auto", "woocommerce", "shopify", "scraper"])
    p.add_argument("--consumer-key",     default="", help="WooCommerce consumer key")
    p.add_argument("--consumer-secret",  default="", help="WooCommerce consumer secret")
    p.add_argument("--storefront-token", default="", help="Shopify storefront access token")
    p.add_argument("--gateway-url",      default="http://localhost:9000")
    return p.parse_args()


async def _main() -> None:
    args = _parse_args()
    creds: Dict[str, str] = {}
    if args.consumer_key:
        creds["consumer_key"]    = args.consumer_key
        creds["consumer_secret"] = args.consumer_secret
    if args.storefront_token:
        creds["storefront_token"] = args.storefront_token

    count = await run_ingestion(
        site_url   = args.url,
        tenant_id  = args.tenant_id,
        platform   = args.platform,
        credentials= creds,
        gateway_url= args.gateway_url,
    )
    logger.info(f"Done. {count} products indexed.")


if __name__ == "__main__":
    asyncio.run(_main())
