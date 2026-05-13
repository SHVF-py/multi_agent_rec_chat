"""
WooCommerce REST API v3 connector.

Credentials required (generated in WC admin → Settings → Advanced → REST API):
  consumer_key    e.g. ck_xxxxxxxxxxxx
  consumer_secret e.g. cs_xxxxxxxxxxxx

Products endpoint: GET {base_url}/wp-json/wc/v3/products
  - Paginates automatically (100 products per page)
  - Works on any WooCommerce 3.0+ site with permalinks enabled
"""
from __future__ import annotations

import logging
from typing import List
from urllib.parse import urljoin

import httpx

from data.connectors.base import BaseConnector, ProductMetadata

logger = logging.getLogger(__name__)

_PER_PAGE = 100


class WooCommerceConnector(BaseConnector):
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str):
        # Normalise base URL
        self.base_url = base_url.rstrip("/")
        self.auth     = (consumer_key, consumer_secret)

    async def fetch_products(self) -> List[ProductMetadata]:
        products: List[ProductMetadata] = []
        page = 1

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                url = f"{self.base_url}/wp-json/wc/v3/products"
                params = {
                    "per_page": _PER_PAGE,
                    "page":     page,
                    "status":   "publish",
                }
                try:
                    resp = await client.get(url, params=params, auth=self.auth)
                    resp.raise_for_status()
                    items = resp.json()
                except Exception as exc:
                    logger.error(f"WooCommerce page {page} failed: {exc}")
                    break

                if not items:
                    break

                for raw in items:
                    p = self._map(raw)
                    if p:
                        products.append(p)

                logger.info(f"WooCommerce: fetched page {page} ({len(items)} products)")
                if len(items) < _PER_PAGE:
                    break
                page += 1

        logger.info(f"WooCommerce: total {len(products)} products")
        return products

    # ------------------------------------------------------------------

    def _map(self, raw: dict) -> ProductMetadata | None:
        pid   = str(raw.get("id", ""))
        name  = raw.get("name", "").strip()
        if not pid or not name:
            return None

        price_str = raw.get("price") or raw.get("regular_price") or "0"
        try:
            price = float(price_str)
        except (ValueError, TypeError):
            price = 0.0

        # Categories — join first two for a readable label
        cats = [c.get("name", "") for c in raw.get("categories", [])]
        category = cats[0] if cats else "general"

        # Brand from attributes (common in WooCommerce)
        brand = "Unbranded"
        for attr in raw.get("attributes", []):
            if attr.get("name", "").lower() in ("brand", "manufacturer"):
                opts = attr.get("options", [])
                if opts:
                    brand = opts[0]
                    break

        # First image
        images = raw.get("images", [])
        image  = images[0].get("src", "") if images else ""

        in_stock = raw.get("stock_status", "instock") == "instock"
        stock_qty = raw.get("stock_quantity") or (50 if in_stock else 0)

        rating_str = raw.get("average_rating", "0")
        try:
            rating = float(rating_str)
        except (ValueError, TypeError):
            rating = 0.0

        description = _strip_html(
            raw.get("short_description") or raw.get("description", "")
        )[:600]

        permalink = raw.get("permalink", "")

        return ProductMetadata(
            product_id    = pid,
            name          = name,
            price         = price,
            description   = description,
            category      = category,
            brand         = brand,
            image         = image,
            in_stock      = in_stock,
            stock_quantity= int(stock_qty) if stock_qty else 0,
            rating        = rating,
            sku           = raw.get("sku", ""),
            url           = permalink,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """Remove HTML tags without BeautifulSoup (fast, no import needed)."""
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()
