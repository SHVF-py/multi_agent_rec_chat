"""
Web scraper connector — platform-agnostic fallback for Wix, Weebly,
Squarespace, and any other site without a public API.

Extraction waterfall (tries each tier, stops at first success per page):
  Tier 1 — Schema.org JSON-LD  (<script type="application/ld+json"> @type Product)
  Tier 2 — Open Graph meta tags (og:title, og:description, og:image, og:price:amount)
  Tier 3 — CSS heuristics (common class/id names for title, price, description)

Crawl strategy:
  1. Fetch the provided URL (home or /shop /products /catalog page)
  2. Find all internal links that look like product pages
     (contain /product/ /item/ /p/ etc., or carry JSON-LD Product)
  3. Scrape each discovered product page
  4. Deduplicate by URL

NOTE: The merchant authorises this scrape during onboarding — consent is
on record, which handles ToS exposure for the merchant's own site.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from data.connectors.base import BaseConnector, ProductMetadata

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Quiribot/1.0; +https://quiribot.com/bot)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# URL path fragments that usually indicate a product page
_PRODUCT_PATH_HINTS = {
    "/product/", "/products/", "/item/", "/items/",
    "/shop/", "/p/", "/pd/", "/catalog/",
    "/collections/", "/goods/",
}

_MAX_PRODUCTS = 200   # safety cap — stops runaway crawls


class ScraperConnector(BaseConnector):
    def __init__(self, site_url: str):
        self.site_url = site_url.rstrip("/")
        parsed        = urlparse(self.site_url)
        self.origin   = f"{parsed.scheme}://{parsed.netloc}"

    async def fetch_products(self) -> List[ProductMetadata]:
        product_urls: Set[str] = set()
        products: List[ProductMetadata] = []

        async with httpx.AsyncClient(
            timeout=20.0, headers=_HEADERS, follow_redirects=True
        ) as client:
            # ── Tier 0: JS data-file scrape (single-page / headless storefronts) ──
            # Tries to fetch app.js / main.js and parse an inline `const products`
            # or `const laptops` array. Works for pure-JS storefronts with no HTML
            # product pages (e.g. the LaptopZone demo site).
            js_products = await self._from_js_datafile(client)
            if js_products:
                logger.info(
                    f"Scraper Tier 0 (JS datafile): extracted {len(js_products)} products"
                )
                return js_products

            # ── Tier 1-3: Standard HTML crawl ────────────────────────────────────
            await self._discover_urls(client, self.site_url, product_urls)

            # If entry page yielded nothing useful, also try /shop and /products
            for suffix in ("/shop", "/products", "/catalog", "/store"):
                if len(product_urls) >= 10:
                    break
                await self._discover_urls(client, self.site_url + suffix, product_urls)

            logger.info(f"Scraper: discovered {len(product_urls)} candidate product URLs")

            # Step 2: Scrape each product page
            for url in list(product_urls)[:_MAX_PRODUCTS]:
                p = await self._scrape_product(client, url)
                if p:
                    products.append(p)

        logger.info(f"Scraper: extracted {len(products)} products from {self.site_url}")
        return products

    # ------------------------------------------------------------------
    # Tier 0: JS datafile parser
    # ------------------------------------------------------------------

    # Candidate JS bundle filenames to probe, in priority order
    _JS_CANDIDATES = ["app.js", "main.js", "products.js", "data.js", "store.js"]

    # Variable names that typically hold the product array
    _ARRAY_VAR_PATTERNS = [
        r"const\s+laptops\s*=\s*(\[[\s\S]*?\n\])",
        r"const\s+products\s*=\s*(\[[\s\S]*?\n\])",
        r"var\s+products\s*=\s*(\[[\s\S]*?\n\])",
        r"let\s+products\s*=\s*(\[[\s\S]*?\n\])",
        r"const\s+items\s*=\s*(\[[\s\S]*?\n\])",
        r"window\.products\s*=\s*(\[[\s\S]*?\n\])",
    ]

    async def _from_js_datafile(self, client: httpx.AsyncClient) -> List[ProductMetadata]:
        """
        Probe known JS bundle filenames for an inline product array and parse it.
        Handles trailing commas and other JS-specific syntax that JSON won't parse.
        """
        for filename in self._JS_CANDIDATES:
            url = f"{self.site_url}/{filename}"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
            except Exception:
                continue

            js_text = resp.text
            for pattern in self._ARRAY_VAR_PATTERNS:
                m = re.search(pattern, js_text, re.DOTALL)
                if not m:
                    continue

                raw_array = m.group(1)
                products  = self._parse_js_object_array(raw_array, filename)
                if products:
                    return products

        return []

    def _parse_js_object_array(self, raw: str, source: str) -> List[ProductMetadata]:
        """
        Convert a raw JS array literal into ProductMetadata objects.
        Uses regex field extraction so trailing commas / unquoted keys are fine.
        """
        products: List[ProductMetadata] = []

        # Split into individual object literals  {  ...  }
        obj_pattern = re.compile(r"\{([^{}]+)\}", re.DOTALL)

        for idx, match in enumerate(obj_pattern.finditer(raw)):
            body = match.group(1)

            def field(key: str, default: str = "") -> str:
                m = re.search(
                    rf'["\']?{key}["\']?\s*:\s*["\']([^"\']*)["\']', body
                )
                return m.group(1).strip() if m else default

            def num_field(key: str, default: float = 0.0) -> float:
                m = re.search(rf'["\']?{key}["\']?\s*:\s*([\d.]+)', body)
                try:
                    return float(m.group(1)) if m else default
                except ValueError:
                    return default

            def bool_field(key: str, default: bool = False) -> bool:
                m = re.search(rf'["\']?{key}["\']?\s*:\s*(true|false)', body)
                if m:
                    return m.group(1) == "true"
                return default

            name = field("name")
            if not name or len(name) < 3:
                continue  # skip non-product objects

            price   = num_field("price")
            img     = field("img")
            rating  = num_field("rating", 4.0)
            badge   = field("badge", "")
            pid_raw = num_field("id", idx + 1)
            pid     = f"{source}-{int(pid_raw)}"

            # Derive category from name keywords
            name_lower = name.lower()
            if any(k in name_lower for k in ("zbook", "quadro", "workstation")):
                category = "workstation"
            elif "spectre" in name_lower or "dragonfly" in name_lower:
                category = "premium"
            elif "probook" in name_lower:
                category = "business"
            else:
                category = "laptop"

            # Brand always HP for this store
            brand = "HP" if "hp" in name_lower or "hp" in self.site_url.lower() else "Unknown"

            # Build a clean description from the name segments
            desc = name.replace(" | ", " — ")

            products.append(ProductMetadata(
                product_id   = pid,
                name         = name,
                price        = price,
                description  = desc,
                category     = category,
                brand        = brand,
                image        = img,
                in_stock     = True,
                stock_quantity = 10,
                rating       = rating,
                sku          = pid,
                url          = self.site_url,
            ))

        return products

    # ------------------------------------------------------------------
    # URL Discovery
    # ------------------------------------------------------------------

    async def _discover_urls(
        self, client: httpx.AsyncClient, url: str, found: Set[str]
    ) -> None:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"Scraper discovery failed for {url}: {exc}")
            return

        soup = BeautifulSoup(resp.text, "lxml")

        # 1a. JSON-LD ItemList → direct product URLs
        for tag in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("ItemList", "CollectionPage"):
                    for el in item.get("itemListElement", []):
                        u = el.get("url") or el.get("item", {}).get("url")
                        if u:
                            found.add(self._abs(u))
                elif item.get("@type") == "Product":
                    u = item.get("url") or url
                    found.add(self._abs(u))

        # 1b. Anchor tags with product-like paths
        for a in soup.find_all("a", href=True):
            href = a["href"]
            abs_href = self._abs(href)
            if not abs_href.startswith(self.origin):
                continue
            path = urlparse(abs_href).path.lower()
            if any(hint in path for hint in _PRODUCT_PATH_HINTS):
                found.add(abs_href)

    # ------------------------------------------------------------------
    # Per-page Extraction (3-tier waterfall)
    # ------------------------------------------------------------------

    async def _scrape_product(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[ProductMetadata]:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            logger.debug(f"Scraper: failed to fetch {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Tier 1: Schema.org JSON-LD
        p = self._from_jsonld(soup, url)
        if p:
            return p

        # Tier 2: Open Graph
        p = self._from_opengraph(soup, url)
        if p:
            return p

        # Tier 3: CSS heuristics
        return self._from_heuristics(soup, url)

    # ------------------------------------------------------------------

    def _from_jsonld(self, soup: BeautifulSoup, url: str) -> Optional[ProductMetadata]:
        for tag in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") != "Product":
                    continue

                name = item.get("name", "").strip()
                if not name:
                    continue

                desc  = _strip_tags(item.get("description", ""))[:600]
                image = _first_image(item.get("image"))
                brand = _nested(item, "brand", "name") or "Unbranded"
                cat   = _nested(item, "category") or "general"
                sku   = item.get("sku", "")

                # Price from offers array / single offer
                offers = item.get("offers", item.get("offer"))
                price  = 0.0
                in_stock = True
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if isinstance(offers, dict):
                    try:
                        price = float(offers.get("price", 0))
                    except (ValueError, TypeError):
                        pass
                    avail = offers.get("availability", "")
                    in_stock = "OutOfStock" not in avail

                # Rating
                rating = 0.0
                agg = item.get("aggregateRating", {})
                if isinstance(agg, dict):
                    try:
                        rating = float(agg.get("ratingValue", 0))
                    except (ValueError, TypeError):
                        pass

                pid = sku or _url_slug(url)
                return ProductMetadata(
                    product_id=pid, name=name, price=price,
                    description=desc, category=cat, brand=brand,
                    image=image, in_stock=in_stock,
                    stock_quantity=50 if in_stock else 0,
                    rating=rating, sku=sku, url=url,
                )
        return None

    def _from_opengraph(self, soup: BeautifulSoup, url: str) -> Optional[ProductMetadata]:
        def og(prop: str) -> str:
            tag = soup.find("meta", property=f"og:{prop}")
            return (tag.get("content", "") if tag else "").strip()

        name = og("title")
        if not name:
            return None

        desc  = og("description")[:600]
        image = og("image")
        price_str = og("price:amount") or og("product:price:amount")
        try:
            price = float(price_str) if price_str else 0.0
        except ValueError:
            price = 0.0

        return ProductMetadata(
            product_id=_url_slug(url),
            name=name, price=price, description=desc,
            category="general", brand="Unbranded",
            image=image, in_stock=True, url=url,
        )

    def _from_heuristics(self, soup: BeautifulSoup, url: str) -> Optional[ProductMetadata]:
        """Last-resort CSS class / tag heuristics."""
        # Title
        title_selectors = [
            "h1.product-title", "h1.product_title", "h1.product-name",
            "[class*='product-title']", "[class*='product_title']",
            "[itemprop='name']", "h1",
        ]
        name = ""
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                name = el.get_text(strip=True)
                if name:
                    break

        if not name or len(name) < 3:
            return None

        # Price
        price = 0.0
        price_selectors = [
            "[class*='price']", "[itemprop='price']",
            "[class*='amount']", ".woocommerce-Price-amount",
        ]
        for sel in price_selectors:
            el = soup.select_one(sel)
            if el:
                raw = re.sub(r"[^\d.]", "", el.get_text())
                try:
                    price = float(raw)
                    break
                except ValueError:
                    pass

        # Description
        desc = ""
        for sel in ["[itemprop='description']", ".product-description",
                    ".product_description", "#product-description", ".description"]:
            el = soup.select_one(sel)
            if el:
                desc = el.get_text(" ", strip=True)[:600]
                break

        # Image
        image = ""
        for sel in [".product-image img", ".product_image img",
                    "[itemprop='image']", ".wp-post-image"]:
            el = soup.select_one(sel)
            if el:
                image = el.get("src") or el.get("data-src", "")
                if image:
                    break

        return ProductMetadata(
            product_id=_url_slug(url),
            name=name, price=price, description=desc,
            category="general", brand="Unbranded",
            image=image, in_stock=True, url=url,
        )

    # ------------------------------------------------------------------

    def _abs(self, href: str) -> str:
        return urljoin(self.origin, href)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _first_image(val) -> str:
    if not val:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        first = val[0]
        if isinstance(first, dict):
            return first.get("url", first.get("contentUrl", ""))
        return str(first)
    if isinstance(val, dict):
        return val.get("url", val.get("contentUrl", ""))
    return ""


def _nested(d: dict, *keys: str) -> str:
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, {})
        else:
            return str(d) if d else ""
    return str(d) if d else ""


def _url_slug(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] or url[-20:]
