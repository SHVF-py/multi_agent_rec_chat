"""
Pydantic schemas for multi-tenant business accounts and widget configuration.
Used by both the portal (db layer) and the API (widget config endpoint).
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class WidgetConfig(BaseModel):
    """Customisation options exposed in the Business Admin panel."""
    bot_name: str = "Quiribot"
    greeting: str = "Hi! How can I help you find the perfect product today?"
    primary_color: str = "#6366f1"
    button_color: str = "#6366f1"
    position: str = "bottom-right"       # bottom-right | bottom-left
    tone: str = "friendly"               # friendly | professional | concise
    blocked_topics: List[str] = Field(default_factory=list)
    avatar_visible: bool = True


class BusinessAccount(BaseModel):
    """A subscribed business / merchant."""
    id: str                              # UUID
    name: str
    website_url: str
    email: str
    status: str = "pending"             # pending | under_review | approved | rejected | suspended
    platform: Optional[str] = None      # woocommerce | shopify | scraper
    # credentials stored as a JSON string (sensitive — never logged)
    platform_credentials: Optional[str] = None
    site_key: str                        # widget API key
    created_at: str
    approved_at: Optional[str] = None
    last_active: Optional[str] = None
    rejection_reason: Optional[str] = None
    product_count: int = 0
    last_sync: Optional[str] = None
    total_conversations: int = 0
    widget_config: WidgetConfig = Field(default_factory=WidgetConfig)


class SyncJob(BaseModel):
    """Represents a catalog sync triggered by a business."""
    id: str
    business_id: str
    status: str = "queued"              # queued | running | done | failed
    products_found: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


# ---------------------------------------------------------------------------
# API response models (returned to the widget JS)
# ---------------------------------------------------------------------------

class WidgetConfigResponse(BaseModel):
    """Subset of WidgetConfig returned to the JS widget (no sensitive data)."""
    bot_name: str
    greeting: str
    primary_color: str
    button_color: str
    position: str
    tone: str
    blocked_topics: List[str]
    avatar_visible: bool
    tenant_id: str                      # resolved from siteKey


class ProactiveResponse(BaseModel):
    """Returned when the current page URL matches a known product."""
    triggered: bool
    product_name: Optional[str] = None
    message: Optional[str] = None
