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

    # Variable names that typically hold the product array.
    # Patterns try the semicolon-terminated form first (e.g. `const laptops = [...];`)
    # then fall back to bare `[...]` to handle all common JS styles.
    _ARRAY_VAR_PATTERNS = [
        r"const\s+laptops\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        r"const\s+products\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        r"var\s+products\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        r"let\s+products\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        r"const\s+items\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        r"window\.products\s*=\s*(\[[\s\S]*?\n\s*\])\s*;",
        # Fallbacks without semicolon
        r"const\s+laptops\s*=\s*(\[[\s\S]*?\n\s*\])",
        r"const\s+products\s*=\s*(\[[\s\S]*?\n\s*\])",
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

        Handles the full laptopzone.pk extended schema:
          name, price, img, rating, badge, id,
          processor, processorGen, ram, storage, display, os, battery,
          weight, condition, sku, description, tags[], specs[]

        Trailing commas and unquoted keys are tolerated.
        """
        products: List[ProductMetadata] = []
        obj_pattern = re.compile(r"\{([^{}]+)\}", re.DOTALL)

        for idx, match in enumerate(obj_pattern.finditer(raw)):
            body = match.group(1)

            def field(key: str, default: str = "") -> str:
                """Extract a string-valued JS property (double or single quoted)."""
                # Double-quoted — handles \n and \" escape sequences
                m = re.search(
                    rf'["\']?{re.escape(key)}["\']?\s*:\s*"((?:[^"\\]|\\.)*)"',
                    body, re.DOTALL,
                )
                if m:
                    return (m.group(1)
                            .replace("\\n", "\n")
                            .replace('\\"', '"')
                            .strip())
                # Single-quoted
                m = re.search(
                    rf'["\']?{re.escape(key)}["\']?\s*:\s*\'((?:[^\'\\]|\\.)*)\'',
                    body, re.DOTALL,
                )
                return m.group(1).replace("\\n", "\n").strip() if m else default

            def num_field(key: str, default: float = 0.0) -> float:
                m = re.search(rf'["\']?{re.escape(key)}["\']?\s*:\s*([\d.]+)', body)
                try:
                    return float(m.group(1)) if m else default
                except ValueError:
                    return default

            def arr_field(key: str) -> List[str]:
                """Extract a flat JS string array: key: ["a", "b", ...]"""
                m = re.search(
                    rf'["\']?{re.escape(key)}["\']?\s*:\s*\[([^\]]*)\]', body
                )
                if not m:
                    return []
                pairs = re.findall(r'"([^"]*?)"|\'([^\']*?)\'', m.group(1))
                return [a or b for (a, b) in pairs if a or b]

            name = field("name")
            if not name or len(name) < 3:
                continue

            price   = num_field("price")
            img     = field("img")
            rating  = num_field("rating", 4.0)
            badge   = field("badge", "Pre-Owned")
            pid_raw = int(num_field("id", idx + 1))

            # ── Extended laptopzone.pk schema fields ──────────────────────
            processor     = field("processor")
            processor_gen = field("processorGen")
            ram           = field("ram")
            storage       = field("storage")
            display       = field("display")
            os_val        = field("os")
            battery       = field("battery")
            weight        = field("weight")
            condition     = field("condition", badge)
            sku           = field("sku")
            description   = field("description")
            tags          = arr_field("tags") or arr_field("specs")

            # Fallback: parse spec hints from the pipe-delimited product name
            if not processor and "|" in name:
                parsed        = _parse_hp_laptop_name(name)
                processor     = processor     or parsed.get("processor", "")
                processor_gen = processor_gen or parsed.get("processorGen", "")
                ram           = ram           or parsed.get("ram", "")
                storage       = storage       or parsed.get("storage", "")
                display       = display       or parsed.get("display", "")

            # ── Category detection ────────────────────────────────────────
            name_lower = name.lower()
            if any(k in name_lower for k in ("zbook", "quadro", "workstation")):
                category = "workstation"
            elif "spectre" in name_lower or "dragonfly" in name_lower:
                category = "premium"
            elif "probook" in name_lower:
                category = "business"
            else:
                category = "laptop"

            brand = (
                "HP"
                if "hp" in name_lower or "hp" in self.site_url.lower()
                else "Unknown"
            )

            # ── Build rich embedding description ─────────────────────────
            if not description:
                description = name.replace(" | ", " — ")

            spec_parts: List[str] = []
            if processor:     spec_parts.append(f"Processor: {processor}")
            if processor_gen: spec_parts.append(f"Generation: {processor_gen}")
            if ram:           spec_parts.append(f"RAM: {ram}")
            if storage:       spec_parts.append(f"Storage: {storage}")
            if display:       spec_parts.append(f"Display: {display}")
            if os_val:        spec_parts.append(f"OS: {os_val}")
            if battery:       spec_parts.append(f"Battery: {battery}")
            if weight:        spec_parts.append(f"Weight: {weight}")
            if condition:     spec_parts.append(f"Condition: {condition}")
            if tags:          spec_parts.append(f"Tags: {', '.join(tags)}")
            if spec_parts:
                description = description + "\n" + " | ".join(spec_parts)

            # Per-product URL — SPA stores use ?product_id=N routing
            product_url = f"{self.site_url}/?product_id={pid_raw}"

            products.append(ProductMetadata(
                product_id    = f"{source}-{pid_raw}",
                name          = name,
                price         = price,
                description   = description,
                category      = category,
                brand         = brand,
                image         = img,
                in_stock      = True,
                stock_quantity= 10,
                rating        = rating,
                sku           = sku or f"{source}-{pid_raw}",
                url           = product_url,
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
        """Last-resort CSS class / tag heuristics.

        Covers generic storefronts and is biased towards the WooCommerce /
        laptopzone.pk HTML structure where a product page is a standard
        WordPress/WooCommerce single-product page.
        """
        # ── Title ─────────────────────────────────────────────
        title_selectors = [
            # WooCommerce
            "h1.product_title",
            "h1.product-title",
            ".product_title.entry-title",
            # Generic
            "h1.product-name",
            "[class*='product-title']",
            "[class*='product_title']",
            "[itemprop='name']",
            "h1",
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

        # ── Price ─────────────────────────────────────────────
        price = 0.0
        price_selectors = [
            # WooCommerce
            ".woocommerce-Price-amount",
            "bdi",   # WooCommerce wraps the price number in <bdi>
            "[itemprop='price']",
            "[class*='price']",
            "[class*='amount']",
        ]
        for sel in price_selectors:
            el = soup.select_one(sel)
            if el:
                raw = re.sub(r"[^\d.]", "", el.get_text())
                try:
                    price = float(raw)
                    if price > 0:
                        break
                except ValueError:
                    pass

        # ── Description ────────────────────────────────────────
        desc = ""
        for sel in [
            # WooCommerce
            ".woocommerce-product-details__short-description",
            "#tab-description",
            ".woocommerce-Tabs-panel--description",
            # Generic
            "[itemprop='description']",
            ".product-description",
            ".product_description",
            "#product-description",
            ".description",
        ]:
            el = soup.select_one(sel)
            if el:
                desc = el.get_text(" ", strip=True)[:600]
                break

        # ── Spec table (WooCommerce Additional Information tab) ───
        spec_lines: list = []
        spec_table = soup.select_one(".woocommerce-product-attributes, #tab-additional_information table")
        if spec_table:
            for row in spec_table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in row.find_all(["th", "td"])]
                if len(cells) >= 2:
                    spec_lines.append(f"{cells[0]}: {cells[1]}")
        if spec_lines:
            desc = desc + ("\n" if desc else "") + " | ".join(spec_lines[:10])

        # Fallback: parse specs from the name (common for laptopzone.pk listings)
        if not desc or len(desc) < 20:
            parsed = _parse_hp_laptop_name(name)
            parts = []
            for k, v in parsed.items():
                parts.append(f"{k}: {v}")
            if parts:
                desc = name.replace(" | ", " — ") + "\n" + " | ".join(parts)

        # ── Image ─────────────────────────────────────────────
        image = ""
        for sel in [
            # WooCommerce
            ".woocommerce-product-gallery__image img",
            ".woocommerce-product-gallery img",
            # Generic
            ".product-image img",
            ".product_image img",
            "[itemprop='image']",
            ".wp-post-image",
        ]:
            el = soup.select_one(sel)
            if el:
                image = el.get("src") or el.get("data-src", "")
                if image:
                    break

        # ── Brand / Category from WooCommerce taxonomy ─────────
        brand = "Unbranded"
        brand_el = soup.select_one(
            ".woocommerce-product-attributes-item--attribute_pa_brand td"
            ", [class*='brand'] span"
        )
        if brand_el:
            brand = brand_el.get_text(strip=True) or brand
        elif "hp" in name.lower() or "hp" in url.lower():
            brand = "HP"

        category = "laptop"
        cat_el = soup.select_one(".posted_in a, .product_cat a")
        if cat_el:
            category = cat_el.get_text(strip=True).lower()

        # Use _parse_hp_laptop_name for better category hints
        parsed = _parse_hp_laptop_name(name)
        name_lower = name.lower()
        if any(k in name_lower for k in ("zbook", "quadro", "workstation")):
            category = "workstation"
        elif "spectre" in name_lower or "dragonfly" in name_lower:
            category = "premium"
        elif "probook" in name_lower:
            category = "business"

        return ProductMetadata(
            product_id = _url_slug(url),
            name       = name,
            price      = price,
            description= desc,
            category   = category,
            brand      = brand,
            image      = image,
            in_stock   = True,
            url        = url,
        )

    # ------------------------------------------------------------------

    def _abs(self, href: str) -> str:
        return urljoin(self.origin, href)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _parse_hp_laptop_name(name: str) -> dict:
    """
    Extract structured spec hints from HP laptop naming conventions used by
    laptopzone.pk and similar stores.

    Handles patterns like:
      "HP EliteBook 840 G7 | i5 10th Gen 10310U | 14 inch 1080p | 8GB RAM 256GB SSD"
      "HP ProBook 450 G9 | i5 12th Gen 1245U | 16GB RAM 256GB SSD | 15\" 1080P"
    """
    result: dict = {}
    parts = [p.strip() for p in name.split("|")]

    for part in parts:
        pl = part.lower()

        # Processor model: i5-1245U, i7-10610U, Ultra 7 155H
        if "processor" not in result:
            m = re.search(
                r"(?:Intel\s+Core\s+)?((?:i[3579]|Ultra\s+\d+)[-\s][\w]+)",
                part, re.IGNORECASE,
            )
            if m:
                result["processor"] = m.group(1).strip()

        # Generation: 10th Gen, 12th Gen
        if "processorGen" not in result:
            m = re.search(r"(\d+)(?:st|nd|rd|th)\s+Gen", part, re.IGNORECASE)
            if m:
                result["processorGen"] = m.group(1) + "th Gen"

        # RAM: 8GB / 16GB / 32GB followed by RAM or DDR
        if "ram" not in result:
            m = re.search(r"(\d+\s*GB)\s+(?:DDR[\dLPx]*|LPDDR[\dx]*|RAM)", part, re.IGNORECASE)
            if not m:
                m = re.search(r"(\d+\s*GB)\s+RAM", part, re.IGNORECASE)
            if m:
                result["ram"] = m.group(0).strip()

        # Storage: 256GB SSD / 512GB NVMe
        if "storage" not in result:
            m = re.search(r"(\d+\s*(?:GB|TB))\s+(?:NVMe|SSD|HDD|Gen[\d ])", part, re.IGNORECASE)
            if m:
                result["storage"] = m.group(0).strip()

        # Display size: 14", 15.6 inch
        if "display" not in result:
            m = re.search(r'([\d.]+)\s*(?:inch|")', part, re.IGNORECASE)
            if m:
                size = m.group(1) + '"'
                res = re.search(r"(1080[pP]|FHD|2K|4K|QHD|WUXGA)", part)
                result["display"] = size + (" " + res.group(1) if res else "")

    return result


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
