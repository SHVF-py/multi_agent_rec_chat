"""
Session store for persisting user history and preferences across conversation turns.

Backed by an in-memory dict with optional JSON file persistence.
The module-level ``session_store`` singleton is imported by the orchestrator.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Tracks per-session state so personalisation and comparison improve over time.

    Stored per session_id:
    - viewed_product_ids     : products already shown (fed to MBA to avoid repeats)
    - preferred_categories   : accumulated from categories of shown products
    - preferred_brands       : accumulated from brands of shown products
    - last_ranked_products   : top-5 products from the most recent retrieval turn
                               (used as comparison fallback when the user says
                               "compare those" without naming products explicitly)
    - interaction_count      : number of product-returning turns so far
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load_from_disk()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Return session data, creating a fresh entry if needed."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "viewed_product_ids": [],
                "preferred_categories": [],
                "preferred_brands": [],
                "last_ranked_products": [],
                "interaction_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        return self._sessions[session_id]

    def update_after_response(
        self,
        session_id: str,
        ranked_products: list,  # List[RankedProduct]
    ) -> None:
        """
        Called by the orchestrator after each turn that returns ranked products.

        Updates:
        - viewed product IDs (capped at last 50)
        - preferred categories and brands (capped at last 10 each)
        - last_ranked_products snapshot (top 5, stored as plain dicts)
        """
        if not ranked_products:
            return

        session = self.get_session(session_id)
        seen_ids = set(session["viewed_product_ids"])
        seen_cats = set(session["preferred_categories"])
        seen_brands = set(session["preferred_brands"])

        for p in ranked_products[:5]:
            pid = p.product_id if hasattr(p, "product_id") else p.get("product_id", "")
            meta = p.metadata if hasattr(p, "metadata") else p.get("metadata", {})

            if pid and pid not in seen_ids:
                session["viewed_product_ids"].append(pid)
                seen_ids.add(pid)

            cat = meta.get("category", "")
            if cat and cat not in seen_cats:
                session["preferred_categories"].append(cat)
                seen_cats.add(cat)

            brand = meta.get("brand", "")
            if brand and brand not in seen_brands and brand.lower() != "unbranded":
                session["preferred_brands"].append(brand)
                seen_brands.add(brand)

        # Cap lists to avoid unbounded growth
        session["viewed_product_ids"] = session["viewed_product_ids"][-50:]
        session["preferred_categories"] = session["preferred_categories"][-10:]
        session["preferred_brands"] = session["preferred_brands"][-10:]

        # Persist last results as plain dicts for comparison fallback
        session["last_ranked_products"] = [
            {
                "product_id": p.product_id,
                "rank": p.rank,
                "metadata": p.metadata,
                "scoring": (
                    p.scoring.model_dump()
                    if hasattr(p.scoring, "model_dump")
                    else dict(p.scoring)
                ),
            }
            for p in ranked_products[:5]
        ]

        session["interaction_count"] += 1

        if self._persist_path:
            self._save_to_disk()

        logger.debug(
            f"Session {session_id[:8]}: "
            f"viewed={len(session['viewed_product_ids'])} products, "
            f"cats={session['preferred_categories']}, "
            f"interactions={session['interaction_count']}"
        )

    def get_user_features(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Return a user-features dict suitable for the ranking agent.
        Returns None when there is no interaction history yet (so the ranking
        agent correctly skips personalisation on the very first query).
        """
        session = self.get_session(session_id)
        if session["interaction_count"] == 0:
            return None
        return {
            "history": session["viewed_product_ids"],
            "preferred_categories": session["preferred_categories"],
            "preferred_brands": session["preferred_brands"],
        }

    def get_viewed_product_ids(self, session_id: str) -> List[str]:
        """Return product IDs already shown to this user (passed to MBA agent)."""
        return self.get_session(session_id).get("viewed_product_ids", [])

    def get_last_ranked_products(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Return the top products from the most recent retrieval turn as plain dicts.
        Used by the orchestrator as a comparison fallback when the current query
        returns fewer than 2 products.
        """
        return self.get_session(session_id).get("last_ranked_products", [])

    # ------------------------------------------------------------------
    # Disk persistence helpers
    # ------------------------------------------------------------------

    def _load_from_disk(self) -> None:
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                self._sessions = json.load(f)
            logger.info(
                f"SessionStore: loaded {len(self._sessions)} sessions "
                f"from {self._persist_path}"
            )
        except Exception as exc:
            logger.warning(f"SessionStore: could not load from disk — {exc}")

    def _save_to_disk(self) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f, indent=2)
        except Exception as exc:
            logger.warning(f"SessionStore: could not persist to disk — {exc}")


# Module-level singleton — shared across all requests within the process.
session_store = SessionStore(persist_path="data/sessions.json")
