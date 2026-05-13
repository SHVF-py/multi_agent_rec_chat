"""
SQLite persistence layer for the portal.
All portal state (business accounts, widget configs, sync jobs) lives here.
The API (port 8080) imports resolve_site_key() to look up tenant_id and widget config.

DB file: data/portal.db  (created automatically on first import)
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from models.tenant import BusinessAccount, SyncJob, WidgetConfig

DB_PATH = Path("data/portal.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    id                    TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    website_url           TEXT NOT NULL,
    email                 TEXT NOT NULL UNIQUE,
    password_hash         TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'pending',
    platform              TEXT,
    platform_credentials  TEXT,
    site_key              TEXT UNIQUE,
    created_at            TEXT NOT NULL,
    approved_at           TEXT,
    last_active           TEXT,
    rejection_reason      TEXT,
    product_count         INTEGER DEFAULT 0,
    last_sync             TEXT,
    total_conversations   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS widget_configs (
    business_id     TEXT PRIMARY KEY,
    bot_name        TEXT DEFAULT 'Quiribot',
    greeting        TEXT DEFAULT 'Hi! How can I help you find the perfect product today?',
    primary_color   TEXT DEFAULT '#6366f1',
    button_color    TEXT DEFAULT '#6366f1',
    position        TEXT DEFAULT 'bottom-right',
    tone            TEXT DEFAULT 'friendly',
    blocked_topics  TEXT DEFAULT '[]',
    avatar_visible  INTEGER DEFAULT 1,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL,
    status          TEXT DEFAULT 'queued',
    products_found  INTEGER DEFAULT 0,
    error           TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id           TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    product_id   TEXT,
    product_name TEXT,
    session_id   TEXT,
    created_at   TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Business helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_business(name: str, website_url: str, email: str, password_hash: str) -> BusinessAccount:
    biz_id  = str(uuid.uuid4())
    site_key = str(uuid.uuid4()).replace("-", "")
    now     = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO businesses
               (id, name, website_url, email, password_hash, status, site_key, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (biz_id, name, website_url, email, password_hash, site_key, now),
        )
        conn.execute(
            "INSERT INTO widget_configs (business_id) VALUES (?)",
            (biz_id,),
        )
    return get_business_by_id(biz_id)


def get_business_by_id(biz_id: str) -> Optional[BusinessAccount]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE id = ?", (biz_id,)
        ).fetchone()
        if not row:
            return None
        cfg_row = conn.execute(
            "SELECT * FROM widget_configs WHERE business_id = ?", (biz_id,)
        ).fetchone()
    return _row_to_account(row, cfg_row)


def get_business_by_email(email: str) -> Optional[BusinessAccount]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return None
        cfg_row = conn.execute(
            "SELECT * FROM widget_configs WHERE business_id = ?", (row["id"],)
        ).fetchone()
    return _row_to_account(row, cfg_row)


def get_password_hash(email: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM businesses WHERE email = ?", (email,)
        ).fetchone()
    return row["password_hash"] if row else None


def resolve_site_key(site_key: str) -> Optional[BusinessAccount]:
    """Used by the API to look up tenant_id and widget config from the widget siteKey."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE site_key = ? AND status = 'active'",
            (site_key,)
        ).fetchone()
        if not row:
            return None
        cfg_row = conn.execute(
            "SELECT * FROM widget_configs WHERE business_id = ?", (row["id"],)
        ).fetchone()
    return _row_to_account(row, cfg_row)


def list_businesses(status: Optional[str] = None) -> list[BusinessAccount]:
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM businesses WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM businesses ORDER BY created_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            cfg_row = conn.execute(
                "SELECT * FROM widget_configs WHERE business_id = ?", (row["id"],)
            ).fetchone()
            result.append(_row_to_account(row, cfg_row))
    return result


def update_business_status(biz_id: str, status: str, reason: str = "") -> None:
    now = _now()
    with get_db() as conn:
        if status == "approved":
            conn.execute(
                "UPDATE businesses SET status = ?, approved_at = ? WHERE id = ?",
                (status, now, biz_id),
            )
        else:
            conn.execute(
                "UPDATE businesses SET status = ?, rejection_reason = ? WHERE id = ?",
                (status, reason, biz_id),
            )


def update_widget_config(biz_id: str, config: WidgetConfig) -> None:
    with get_db() as conn:
        conn.execute(
            """UPDATE widget_configs
               SET bot_name=?, greeting=?, primary_color=?, button_color=?,
                   position=?, tone=?, blocked_topics=?, avatar_visible=?
               WHERE business_id=?""",
            (
                config.bot_name, config.greeting, config.primary_color,
                config.button_color, config.position, config.tone,
                json.dumps(config.blocked_topics), int(config.avatar_visible),
                biz_id,
            ),
        )


def update_platform(biz_id: str, platform: str, credentials: dict) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE businesses SET platform=?, platform_credentials=? WHERE id=?",
            (platform, json.dumps(credentials), biz_id),
        )


def update_sync_result(biz_id: str, product_count: int) -> None:
    now = _now()
    with get_db() as conn:
        conn.execute(
            "UPDATE businesses SET product_count=?, last_sync=? WHERE id=?",
            (product_count, now, biz_id),
        )


def increment_conversations(tenant_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE businesses SET total_conversations = total_conversations + 1, "
            "last_active = ? WHERE id = ?",
            (_now(), tenant_id),
        )


def log_chat_event(tenant_id: str, session_id: str) -> None:
    """Record a chat call and bump total_conversations."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, tenant_id, event_type, session_id, created_at) "
            "VALUES (?, ?, 'chat', ?, ?)",
            (str(uuid.uuid4()), tenant_id, session_id, _now()),
        )
        conn.execute(
            "UPDATE businesses SET total_conversations = total_conversations + 1, "
            "last_active = ? WHERE id = ?",
            (_now(), tenant_id),
        )


def log_recommendation_event(
    tenant_id: str, product_id: str, product_name: str, session_id: str
) -> None:
    """Record a product being recommended in a chat."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO analytics_events "
            "(id, tenant_id, event_type, product_id, product_name, session_id, created_at) "
            "VALUES (?, ?, 'recommendation', ?, ?, ?, ?)",
            (str(uuid.uuid4()), tenant_id, product_id, product_name, session_id, _now()),
        )


def get_analytics(tenant_id: str) -> dict:
    """Return aggregated analytics for the business dashboard."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db() as conn:
        chat_today = conn.execute(
            "SELECT COUNT(*) FROM analytics_events "
            "WHERE tenant_id=? AND event_type='chat' AND date(created_at)=?",
            (tenant_id, today),
        ).fetchone()[0]

        users_today = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM analytics_events "
            "WHERE tenant_id=? AND event_type='chat' AND date(created_at)=?",
            (tenant_id, today),
        ).fetchone()[0]

        total_row = conn.execute(
            "SELECT total_conversations FROM businesses WHERE id=?",
            (tenant_id,),
        ).fetchone()
        total_chats = total_row[0] if total_row else 0

        top_rows = conn.execute(
            "SELECT product_name, COUNT(*) as cnt FROM analytics_events "
            "WHERE tenant_id=? AND event_type='recommendation' "
            "GROUP BY product_id ORDER BY cnt DESC LIMIT 5",
            (tenant_id,),
        ).fetchall()
        top_products = [{"name": r["product_name"], "count": r["cnt"]} for r in top_rows]

        week_rows = conn.execute(
            "SELECT date(created_at) as day, COUNT(*) as cnt FROM analytics_events "
            "WHERE tenant_id=? AND event_type='chat' "
            "AND date(created_at) >= date('now', '-6 days') "
            "GROUP BY day ORDER BY day",
            (tenant_id,),
        ).fetchall()
        weekly_calls = [{"day": r["day"], "count": r["cnt"]} for r in week_rows]

    return {
        "chat_calls_today": chat_today,
        "users_today": users_today,
        "total_chats": total_chats,
        "top_products": top_products,
        "weekly_calls": weekly_calls,
    }


# ---------------------------------------------------------------------------
# Sync job helpers
# ---------------------------------------------------------------------------

def create_sync_job(biz_id: str) -> SyncJob:
    job_id = str(uuid.uuid4())
    now    = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sync_jobs (id, business_id, status, started_at) VALUES (?, ?, 'running', ?)",
            (job_id, biz_id, now),
        )
    return SyncJob(id=job_id, business_id=biz_id, status="running", started_at=now)


def finish_sync_job(job_id: str, products_found: int, error: str = "") -> None:
    now = _now()
    status = "done" if not error else "failed"
    with get_db() as conn:
        conn.execute(
            "UPDATE sync_jobs SET status=?, products_found=?, error=?, finished_at=? WHERE id=?",
            (status, products_found, error or None, now, job_id),
        )


def get_latest_sync(biz_id: str) -> Optional[SyncJob]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sync_jobs WHERE business_id = ? ORDER BY started_at DESC LIMIT 1",
            (biz_id,),
        ).fetchone()
    if not row:
        return None
    return SyncJob(
        id=row["id"], business_id=row["business_id"], status=row["status"],
        products_found=row["products_found"], error=row["error"],
        started_at=row["started_at"], finished_at=row["finished_at"],
    )


# ---------------------------------------------------------------------------
# Internal mapper
# ---------------------------------------------------------------------------

def _row_to_account(row: sqlite3.Row, cfg_row: Optional[sqlite3.Row]) -> BusinessAccount:
    cfg = WidgetConfig()
    if cfg_row:
        cfg = WidgetConfig(
            bot_name=cfg_row["bot_name"],
            greeting=cfg_row["greeting"],
            primary_color=cfg_row["primary_color"],
            button_color=cfg_row["button_color"],
            position=cfg_row["position"],
            tone=cfg_row["tone"],
            blocked_topics=json.loads(cfg_row["blocked_topics"] or "[]"),
            avatar_visible=bool(cfg_row["avatar_visible"]),
        )
    return BusinessAccount(
        id=row["id"], name=row["name"], website_url=row["website_url"],
        email=row["email"], status=row["status"], platform=row["platform"],
        platform_credentials=row["platform_credentials"],
        site_key=row["site_key"], created_at=row["created_at"],
        approved_at=row["approved_at"], last_active=row["last_active"],
        rejection_reason=row["rejection_reason"],
        product_count=row["product_count"] or 0,
        last_sync=row["last_sync"],
        total_conversations=row["total_conversations"] or 0,
        widget_config=cfg,
    )


# Initialise schema on import
init_db()
