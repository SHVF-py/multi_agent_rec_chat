"""
One-shot setup script for the LaptopZone dummy website.

What this does:
  1. Creates (or reuses) a LaptopZone business account in the portal DB
  2. Auto-approves it (skipping the owner review step for dev/testing)
  3. Ingests all 12 HP laptops directly into the FAISS vector store
  4. Updates product_count in the portal DB
  5. Prints the siteKey — paste it into the widget snippet in index.html

Run from the project root (with venv active):
    python data/ingest_laptopstore.py
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.connectors.base import ProductMetadata
from data.ingest import _build_association_rules, run_ingestion   # reuse pipeline helpers
import portal.db as pdb
import hashlib as _hashlib

# Use SHA-256 for this setup script to avoid passlib/bcrypt version issues.
# The portal uses bcrypt for login; this script only needs a valid stored hash.
def _simple_hash(plain: str) -> str:
    return "sha256$" + _hashlib.sha256(plain.encode()).hexdigest()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("laptopstore-setup")

# ---------------------------------------------------------------------------
# Product catalogue — mirrored from app.js
# ---------------------------------------------------------------------------
PRODUCTS: list[ProductMetadata] = [
    ProductMetadata(
        product_id="lz-001",
        name="HP EliteBook X360 1030 G7",
        price=123000,
        description="13.3\" 1080p 2-in-1 display, Intel Core i7-10610U 10th Gen, 32GB RAM, 512GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.7,
        image="https://upload.wikimedia.org/wikipedia/commons/9/9a/HP_EliteBook_840_G8.png",
        sku="LZ-001",
    ),
    ProductMetadata(
        product_id="lz-002",
        name="HP ProBook 450 G9",
        price=115000,
        description="15\" 1080p display, Intel Core i5-1245U 12th Gen, 16GB RAM, 256GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.3,
        image="https://upload.wikimedia.org/wikipedia/commons/d/db/HP_EliteBook_850_G5.png",
        sku="LZ-002",
    ),
    ProductMetadata(
        product_id="lz-003",
        name="HP ProBook 640 G9",
        price=90000,
        description="14\" 1080p display, Intel Core i5-1245U 12th Gen, 16GB RAM, 256GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.2,
        image="https://upload.wikimedia.org/wikipedia/commons/d/d7/HP_EliteBook_840_G4.png",
        sku="LZ-003",
    ),
    ProductMetadata(
        product_id="lz-004",
        name="HP EliteBook 830 G7",
        price=73000,
        description="13\" 1080p display, Intel Core i5-10310U 10th Gen, 8GB RAM, 256GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.5,
        image="https://upload.wikimedia.org/wikipedia/commons/c/c5/HP_Elitebook_840_G1.png",
        sku="LZ-004",
    ),
    ProductMetadata(
        product_id="lz-005",
        name="HP EliteBook x360 1030 G2",
        price=68000,
        description="13.3\" 1080p 2-in-1, Intel Core i5-7300U 7th Gen, 8GB RAM, 512GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.4,
        image="https://upload.wikimedia.org/wikipedia/commons/4/48/HP_EliteBook_x360_1020_G2.png",
        sku="LZ-005",
    ),
    ProductMetadata(
        product_id="lz-006",
        name="HP ZBook Firefly 14 G8",
        price=93000,
        description="14\" 1080p, Intel Core i5-1145G7 11th Gen, 16GB RAM, 256GB SSD. Mobile workstation, pre-owned.",
        category="Workstations",
        brand="HP",
        rating=4.6,
        image="https://upload.wikimedia.org/wikipedia/commons/9/9a/HP_EliteBook_840_G8.png",
        sku="LZ-006",
    ),
    ProductMetadata(
        product_id="lz-007",
        name="HP ProBook 650 G8",
        price=97000,
        description="15\" 1080p display, Intel Core i5 11th Gen, 16GB RAM, 256GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.3,
        image="https://upload.wikimedia.org/wikipedia/commons/d/db/HP_EliteBook_850_G5.png",
        sku="LZ-007",
    ),
    ProductMetadata(
        product_id="lz-008",
        name="HP EliteBook 650 G9",
        price=123000,
        description="15\" 1080p display, Intel Core i5 12th Gen, 16GB RAM, 256GB SSD. Pre-owned, tested.",
        category="Laptops",
        brand="HP",
        rating=4.5,
        image="https://upload.wikimedia.org/wikipedia/commons/d/d7/HP_EliteBook_840_G4.png",
        sku="LZ-008",
    ),
    ProductMetadata(
        product_id="lz-009",
        name="HP Spectre X360 16",
        price=317000,
        description="16\" 2K 2-in-1 display, Intel Ultra Core 7 155H, 16GB DDR5, 1TB Gen4 SSD. Brand new.",
        category="Laptops",
        brand="HP",
        rating=4.8,
        image="https://upload.wikimedia.org/wikipedia/commons/1/1b/HP_Spectre_x360_2016_%2832003550180%29.jpg",
        sku="LZ-009",
    ),
    ProductMetadata(
        product_id="lz-010",
        name="HP ZBook Power 15 G8",
        price=175000,
        description="15\" display, Intel Core i7-11850H 11th Gen, 16GB RAM, 512GB SSD, 4GB NVIDIA Quadro T1200. Pre-owned.",
        category="Workstations",
        brand="HP",
        rating=4.7,
        image="https://upload.wikimedia.org/wikipedia/commons/9/96/HP_Elitebook_8770w.png",
        sku="LZ-010",
    ),
    ProductMetadata(
        product_id="lz-011",
        name="HP ZBook 15 G5",
        price=113000,
        description="15\" 1080p, Intel Core i7-8850H 8th Gen, 16GB RAM, 256GB SSD, 4GB NVIDIA Quadro P1000. Pre-owned.",
        category="Workstations",
        brand="HP",
        rating=4.2,
        image="https://upload.wikimedia.org/wikipedia/commons/6/61/HP_EliteBook_8760w_%281%29.jpg",
        sku="LZ-011",
    ),
    ProductMetadata(
        product_id="lz-012",
        name="HP Elite x360 Dragonfly G2",
        price=150000,
        description="13\" 1080p 2-in-1, Intel Core i7-1185G7 11th Gen, 32GB RAM, 256GB SSD. Pre-owned, premium ultra-thin.",
        category="Laptops",
        brand="HP",
        rating=4.6,
        image="https://upload.wikimedia.org/wikipedia/commons/5/5a/HP_Spectre_x360_2016_%2831538364704%29.jpg",
        sku="LZ-012",
    ),
]

TENANT_ID   = "laptopzone"
BIZ_NAME    = "LaptopZone"
BIZ_URL     = "http://localhost:5500"   # e.g. VS Code Live Server default
BIZ_EMAIL   = "owner@laptopzone.pk"
BIZ_PASS    = "admin1234"              # change this for real use
GATEWAY_URL = "http://localhost:9000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _ingest_products(products: list[ProductMetadata], tenant_id: str) -> int:
    """Embed + upsert each product via the gateway."""
    indexed = 0
    async with httpx.AsyncClient(timeout=120.0) as client:
        for p in products:
            embed_text = p.to_embed_text()
            meta       = p.to_metadata_dict(tenant_id)

            try:
                er = await client.post(f"{GATEWAY_URL}/embed/text", json={"text": embed_text})
                er.raise_for_status()
                vector = er.json()["vector"]
            except Exception as exc:
                log.error(f"  Embedding failed for '{p.name}': {exc}")
                continue

            try:
                ur = await client.post(
                    f"{GATEWAY_URL}/vector/text/add",
                    json={"vectors": [vector], "metadata": [meta]},
                )
                ur.raise_for_status()
                indexed += 1
                log.info(f"  ✓ Indexed: {p.name}")
            except Exception as exc:
                log.error(f"  Upsert failed for '{p.name}': {exc}")

    return indexed


def _register_or_get_business() -> pdb.BusinessAccount:
    """Create the LaptopZone business (or return existing one)."""
    existing = pdb.get_business_by_email(BIZ_EMAIL)
    if existing:
        log.info(f"Business already exists (id={existing.id}), reusing.")
        return existing

    pw_hash = _simple_hash(BIZ_PASS)
    biz     = pdb.create_business(BIZ_NAME, BIZ_URL, BIZ_EMAIL, pw_hash)
    log.info(f"Created business: {biz.id}")
    return biz


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    # 1. Register business
    log.info("=== Step 1: Register business in portal ===")
    biz = _register_or_get_business()

    # 2. Auto-approve (skip owner review for dev/testing)
    if biz.status != "approved":
        pdb.update_business_status(biz.id, "approved")
        log.info("Business approved.")
    else:
        log.info("Business already approved.")

    site_key  = biz.site_key
    tenant_id = biz.id          # tenant_id == the business UUID stored with each vector

    log.info(f"  siteKey  : {site_key}")
    log.info(f"  tenant_id: {tenant_id}")

    # 3. Ingest products
    log.info("=== Step 2: Ingest products into FAISS ===")
    job = pdb.create_sync_job(biz.id)

    indexed = await _ingest_products(PRODUCTS, tenant_id)

    # 4. Update portal DB
    pdb.finish_sync_job(job.id, products_found=indexed)
    pdb.update_sync_result(biz.id, product_count=indexed)
    log.info(f"=== Done: {indexed}/{len(PRODUCTS)} products indexed ===")

    # 5. Build association rules
    from pathlib import Path as _Path
    import json as _json
    from config.settings import settings
    rules_path = _Path(settings.MBA_RULES_PATH)
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules = _build_association_rules(PRODUCTS)
    with rules_path.open("w") as f:
        _json.dump(rules, f, indent=2)
    log.info(f"Saved {len(rules)} association rules.")

    # 6. Print widget snippet
    print("\n" + "="*60)
    print("COPY THIS SNIPPET INTO THE <body> OF YOUR index.html")
    print("="*60)
    snippet = f"""<!-- Quiribot widget -->
<script>
  window.QuiribotConfig = {{
    siteKey  : "{site_key}",
    apiUrl   : "http://localhost:8080",
    portalUrl: "http://localhost:7000"
  }};
</script>
<script src="http://localhost:7000/widget/loader.js" defer></script>"""
    print(snippet)
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
