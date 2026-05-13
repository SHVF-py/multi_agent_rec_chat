"""
Authentication utilities for the portal.
- Business users: JWT tokens (signed, 24h expiry)
- Owner: single hardcoded admin verified against env-var credentials
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# ---------------------------------------------------------------------------
# Config — override via environment variables
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("PORTAL_SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 24

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "admin")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "quiribot-owner-2026")  # change in .env

# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT utilities (business users)
# ---------------------------------------------------------------------------

def create_access_token(business_id: str, extra: Optional[dict] = None) -> str:
    expire  = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": business_id, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Return full payload dict on success, None on invalid/expired token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Owner auth (stateless — no DB needed)
# ---------------------------------------------------------------------------

def verify_owner(username: str, password: str) -> bool:
    return username == OWNER_USERNAME and password == OWNER_PASSWORD
