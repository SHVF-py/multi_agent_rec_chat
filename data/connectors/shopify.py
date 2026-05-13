"""
Shopify Storefront API connector (GraphQL, read-only, no OAuth needed).

Credentials required:
  storefront_token  — Public storefront access token
                      (Shopify admin → Apps → Develop apps → Storefront API)

For .myshopify.com stores the base_url is:
  https://{store}.myshopify.com

For custom domains (e.g. mybrand.com) the storefront endpoint is still at
  https://{store}.myshopify.com  — the merchant must provide this.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from data.connectors.base import BaseConnector, ProductMetadata

logger = logging.getLogger(__name__)

_API_VERSION = "2025-01"
_PAGE_SIZE   = 50   # Storefront API max per request

_PRODUCTS_QUERY = """
query Products($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    edges {
      node {
        id
        title
        description
        handle
        productType
        vendor
        tags
        images(first: 1) {
          edges { node { url altText } }
        }
        variants(first: 5) {
          edges {
            node {
              price { amount currencyCode }
              availableForSale
              sku
              title
            }
          }
        }
        onlineStoreUrl
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


class ShopifyConnector(BaseConnector):
    def __init__(self, shop_domain: str, storefront_token: str):
        """
        shop_domain: 'mystore.myshopify.com' or full 'https://mystore.myshopify.com'
        """
        domain = shop_domain.replace("https://", "").replace("http://", "").rstrip("/")
        self.endpoint = (
            f"https://{domain}/api/{_API_VERSION}/graphql.json"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": storefront_token,
        }

    async def fetch_products(self) -> List[ProductMetadata]:
        products: List[ProductMetadata] = []
        cursor: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                variables = {"first": _PAGE_SIZE, "after": cursor}
                try:
                    resp = await client.post(
                        self.endpoint,
                        json={"query": _PRODUCTS_QUERY, "variables": variables},
                        headers=self.headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.error(f"Shopify request failed: {exc}")
                    break

                if "errors" in data:
                    logger.error(f"Shopify GraphQL errors: {data['errors']}")
                    break

                page = data.get("data", {}).get("products", {})
                edges = page.get("edges", [])

                for edge in edges:
                    p = self._map(edge["node"])
                    if p:
                        products.append(p)

                logger.info(f"Shopify: fetched {len(edges)} products (cursor={cursor})")
                page_info = page.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")

        logger.info(f"Shopify: total {len(products)} products")
        return products

    # ------------------------------------------------------------------

    def _map(self, node: dict) -> Optional[ProductMetadata]:
        pid  = node.get("id", "").split("/")[-1]   # gid://shopify/Product/123 → 123
        name = node.get("title", "").strip()
        if not pid or not name:
            return None

        # First variant price
        variants = [e["node"] for e in node.get("variants", {}).get("edges", [])]
        price    = 0.0
        in_stock = False
        sku      = ""
        if variants:
            v = variants[0]
            try:
                price = float(v.get("price", {}).get("amount", 0))
            except (ValueError, TypeError):
                price = 0.0
            in_stock = v.get("availableForSale", False)
            sku      = v.get("sku", "")

        # First image
        imgs  = [e["node"] for e in node.get("images", {}).get("edges", [])]
        image = imgs[0].get("url", "") if imgs else ""

        category = node.get("productType") or "general"
        brand    = node.get("vendor") or "Unbranded"
        desc     = node.get("description", "")[:600]
        url      = node.get("onlineStoreUrl") or ""

        return ProductMetadata(
            product_id    = pid,
            name          = name,
            price         = price,
            description   = desc,
            category      = category,
            brand         = brand,
            image         = image,
            in_stock      = in_stock,
            stock_quantity= 50 if in_stock else 0,
            sku           = sku,
            url           = url,
        )
