"""
CSV / JSON file connector.

Reads products from a previously-uploaded JSON array or CSV file.
Used when the business has uploaded a product file via the portal.

credentials dict must contain:
    upload_path: str  — path to the .json or .csv file
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import List

from data.connectors.base import ProductMetadata

logger = logging.getLogger(__name__)

# Maps canonical ProductMetadata fields to common column name aliases
_FIELD_ALIASES: dict[str, list[str]] = {
    "product_id":  ["product_id", "id", "sku", "product_code"],
    "name":        ["name", "title", "product_name", "product_title"],
    "price":       ["price", "regular_price", "sale_price", "cost"],
    "description": ["description", "desc", "product_description", "details"],
    "category":    ["category", "category_name", "type", "product_type"],
    "brand":       ["brand", "manufacturer", "vendor", "make"],
    "rating":      ["rating", "average_rating", "stars", "score"],
    "image":       ["image", "image_url", "thumbnail", "picture", "photo"],
    "sku":         ["sku", "product_code", "mpn", "barcode"],
}


def _map_row(row: dict) -> dict:
    """Map arbitrary column names to ProductMetadata fields using aliases."""
    low = {k.lower().strip(): v for k, v in row.items()}
    out: dict = {}
    for field, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            if alias in low and low[alias] not in (None, ""):
                out[field] = low[alias]
                break
    return out


def _to_product_metadata(d: dict, fallback_id: str) -> ProductMetadata:
    price_raw = d.get("price", 0)
    try:
        price = float(str(price_raw).replace(",", "").strip()) if price_raw else 0.0
    except (ValueError, TypeError):
        price = 0.0

    rating_raw = d.get("rating", 0)
    try:
        rating = float(rating_raw) if rating_raw else 0.0
    except (ValueError, TypeError):
        rating = 0.0

    return ProductMetadata(
        product_id  = str(d.get("product_id") or fallback_id),
        name        = str(d.get("name") or "Unknown Product"),
        price       = price,
        description = str(d.get("description") or ""),
        category    = str(d.get("category") or "General"),
        brand       = str(d.get("brand") or ""),
        rating      = rating,
        image       = str(d.get("image") or ""),
        sku         = str(d.get("sku") or d.get("product_id") or fallback_id),
    )


class CsvJsonConnector:
    """Connector that reads products from an uploaded .json or .csv file."""

    def __init__(self, upload_path: str):
        self.path = Path(upload_path)

    async def fetch_products(self) -> List[ProductMetadata]:
        if not self.path.exists():
            raise FileNotFoundError(f"Upload file not found: {self.path}")
        suffix = self.path.suffix.lower()
        if suffix == ".json":
            return self._read_json()
        elif suffix == ".csv":
            return self._read_csv()
        else:
            raise ValueError(f"Unsupported file type: {suffix} (must be .json or .csv)")

    def _read_json(self) -> List[ProductMetadata]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a top-level array of product objects")
        products = []
        for i, item in enumerate(data):
            try:
                mapped = _map_row(item)
                products.append(_to_product_metadata(mapped, fallback_id=f"p-{i + 1}"))
            except Exception as exc:
                logger.warning(f"Skipping JSON row {i}: {exc}")
        logger.info(f"Parsed {len(products)} products from JSON")
        return products

    def _read_csv(self) -> List[ProductMetadata]:
        products = []
        with self.path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    mapped = _map_row(dict(row))
                    products.append(_to_product_metadata(mapped, fallback_id=f"p-{i + 1}"))
                except Exception as exc:
                    logger.warning(f"Skipping CSV row {i + 1}: {exc}")
        logger.info(f"Parsed {len(products)} products from CSV")
        return products
