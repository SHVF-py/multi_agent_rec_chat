"""
Base connector interface and shared ProductMetadata schema.
All platform connectors inherit from BaseConnector and return List[ProductMetadata].
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class ProductMetadata:
    """Unified product schema — same fields regardless of source platform."""
    product_id: str
    name: str
    price: float
    description: str
    category: str
    brand: str = "Unbranded"
    image: str = ""
    in_stock: bool = True
    stock_quantity: int = 50
    rating: float = 0.0
    sku: str = ""
    url: str = ""
    source_type: str = "description"
    timestamp: str = "2024-01-01T00:00:00"

    def to_metadata_dict(self, tenant_id: str) -> dict:
        """Convert to the dict format stored alongside FAISS vectors."""
        return {
            "product_id":     self.product_id,
            "name":           self.name,
            "price":          self.price,
            "category":       self.category,
            "brand":          self.brand,
            "rating":         self.rating,
            "stock_quantity": self.stock_quantity,
            "description":    self.description,
            "image":          self.image,
            "in_stock":       self.in_stock,
            "sku":            self.sku,
            "url":            self.url,
            "source_type":    self.source_type,
            "timestamp":      self.timestamp,
            "tenant_id":      tenant_id,
        }

    def to_embed_text(self) -> str:
        """Text sent to the embedding model — mirrors the indexed format."""
        parts = [self.name]
        if self.category:
            parts.append(f"Category: {self.category}")
        if self.description:
            parts.append(self.description[:400])   # truncate very long descriptions
        return ". ".join(parts)


class BaseConnector(ABC):
    """Abstract base — each platform implements fetch_products()."""

    @abstractmethod
    async def fetch_products(self) -> List[ProductMetadata]:
        """Fetch all products from the platform and return unified schema."""
        ...


# ---------------------------------------------------------------------------
# Platform auto-detection
# ---------------------------------------------------------------------------

def detect_platform(site_url: str) -> str:
    """
    Heuristic detection — returns 'woocommerce' | 'shopify' | 'scraper'.
    Checks well-known URL patterns without making any HTTP requests.
    """
    parsed = urlparse(site_url.lower())
    host   = parsed.netloc or parsed.path

    if "myshopify.com" in host:
        return "shopify"

    # WooCommerce check is done at runtime (needs HTTP request to /wp-json/wc/v3/)
    # Shopify custom domains also need runtime check — default to scraper here,
    # and let the ingest pipeline probe the site before falling back.
    return "unknown"
