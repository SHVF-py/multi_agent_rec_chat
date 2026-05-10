"""
Business / merchant admin router — mounts at /business
All protected routes require JWT stored in session cookie.
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from portal.auth import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)
from portal import db as pdb

router    = APIRouter(prefix="/business")
templates = Jinja2Templates(directory="portal/templates")

_SESSION_COOKIE = "qb_biz_session"
_MIN_PASSWORD_LEN = 8


# ---------------------------------------------------------------------------
# Auth guard — returns business dict or redirects
# ---------------------------------------------------------------------------

def _require_business(request: Request) -> dict:
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=307, headers={"Location": "/business/login"})
    payload = decode_access_token(token)
    if not payload or payload.get("role") == "owner":
        raise HTTPException(status_code=307, headers={"Location": "/business/login"})
    business_id = payload.get("sub")
    if not business_id:
        raise HTTPException(status_code=307, headers={"Location": "/business/login"})
    biz = pdb.get_business_by_id(business_id)
    if not biz:
        raise HTTPException(status_code=307, headers={"Location": "/business/login"})
    return dict(biz)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

@router.get("/signup", response_class=HTMLResponse)
async def business_signup_page(request: Request):
    return templates.TemplateResponse(
        "business_signup.html",
        {"request": request, "error": None},
    )


@router.post("/signup")
async def business_signup(
    request: Request,
    name:         str = Form(...),
    website_url:  str = Form(...),
    email:        str = Form(...),
    password:     str = Form(...),
):
    if len(password) < _MIN_PASSWORD_LEN:
        return templates.TemplateResponse(
            "business_signup.html",
            {"request": request, "error": "Password must be at least 8 characters.",
             "name": name, "website_url": website_url, "email": email},
            status_code=400,
        )

    if pdb.get_business_by_email(email):
        return templates.TemplateResponse(
            "business_signup.html",
            {"request": request, "error": "An account with that email already exists.",
             "name": name, "website_url": website_url},
            status_code=400,
        )

    pw_hash = hash_password(password)
    biz     = pdb.create_business(
        name=name, website_url=website_url,
        email=email, password_hash=pw_hash,
    )

    token = create_access_token(biz["id"])
    resp  = RedirectResponse("/business/dashboard", status_code=303)
    resp.set_cookie(_SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=86400)
    return resp


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def business_login_page(request: Request):
    return templates.TemplateResponse(
        "business_login.html",
        {"request": request, "error": None},
    )


@router.post("/login")
async def business_login(
    request: Request,
    email:    str = Form(...),
    password: str = Form(...),
):
    biz = pdb.get_business_by_email(email)
    if not biz:
        return templates.TemplateResponse(
            "business_login.html",
            {"request": request, "error": "No account found with that email."},
            status_code=401,
        )

    pw_hash = pdb.get_password_hash(biz["id"])
    if not verify_password(password, pw_hash):
        return templates.TemplateResponse(
            "business_login.html",
            {"request": request, "error": "Incorrect password."},
            status_code=401,
        )

    token = create_access_token(biz["id"])
    resp  = RedirectResponse("/business/dashboard", status_code=303)
    resp.set_cookie(_SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=86400)
    return resp


@router.get("/logout")
async def business_logout():
    resp = RedirectResponse("/business/login", status_code=303)
    resp.delete_cookie(_SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
async def business_dashboard(
    request: Request,
    biz: dict = Depends(_require_business),
):
    sync_job = pdb.get_latest_sync(biz["id"])

    sync_status = "Never"
    if biz.get("last_sync"):
        sync_status = biz["last_sync"][:10]

    return templates.TemplateResponse(
        "business_dashboard.html",
        {
            "request":     request,
            "business":    biz,
            "sync_job":    dict(sync_job) if sync_job else None,
            "sync_status": sync_status,
        },
    )


# ---------------------------------------------------------------------------
# Onboarding (platform + credentials)
# ---------------------------------------------------------------------------

@router.get("/onboarding", response_class=HTMLResponse)
async def business_onboarding_page(
    request: Request,
    biz: dict = Depends(_require_business),
):
    creds = {}
    try:
        creds = json.loads(biz.get("platform_credentials") or "{}")
    except Exception:
        pass

    return templates.TemplateResponse(
        "business_onboarding.html",
        {
            "request":          request,
            "current_platform": biz.get("platform", ""),
            "creds":            creds,
            "error":            None,
        },
    )


@router.post("/onboarding")
async def business_onboarding_submit(
    request: Request,
    biz: dict = Depends(_require_business),
    platform:         str = Form(default="scraper"),
    consumer_key:     str = Form(default=""),
    consumer_secret:  str = Form(default=""),
    storefront_token: str = Form(default=""),
):
    creds: dict = {}
    if platform == "woocommerce":
        creds = {"consumer_key": consumer_key, "consumer_secret": consumer_secret}
    elif platform == "shopify":
        creds = {"storefront_token": storefront_token}

    pdb.update_platform(biz["id"], platform, creds)
    return RedirectResponse("/business/dashboard", status_code=303)


# ---------------------------------------------------------------------------
# Trigger product sync
# ---------------------------------------------------------------------------

@router.post("/sync")
async def business_sync(
    request: Request,
    biz: dict = Depends(_require_business),
):
    if biz["status"] != "active":
        return RedirectResponse("/business/dashboard?error=not_approved", status_code=303)

    # Record job start
    job_id = pdb.create_sync_job(biz["id"])

    # Run ingestion in background (non-blocking for the web response)
    asyncio.create_task(_run_sync(biz, job_id))

    return RedirectResponse("/business/dashboard", status_code=303)


async def _run_sync(biz: dict, job_id: str) -> None:
    """Background task — runs the ingestion pipeline and updates DB."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
    from data.ingest import run_ingestion

    creds: dict = {}
    try:
        creds = json.loads(biz.get("platform_credentials") or "{}")
    except Exception:
        pass

    try:
        count = await run_ingestion(
            site_url   = biz["website_url"],
            tenant_id  = biz["id"],
            platform   = biz.get("platform") or "auto",
            credentials= creds,
        )
        pdb.finish_sync_job(job_id, status="done", products_found=count)
        pdb.update_sync_result(biz["id"], count)
    except Exception as exc:
        pdb.finish_sync_job(job_id, status="error", error=str(exc))


# ---------------------------------------------------------------------------
# Widget customization
# ---------------------------------------------------------------------------

@router.get("/customize", response_class=HTMLResponse)
async def business_customize_page(
    request: Request,
    biz: dict = Depends(_require_business),
):
    cfg: dict = {}
    try:
        cfg = json.loads(biz.get("widget_config") or "{}")
    except Exception:
        pass

    return templates.TemplateResponse(
        "business_customize.html",
        {"request": request, "business": biz, "cfg": cfg, "success": False},
    )


@router.post("/customize")
async def business_customize_submit(
    request: Request,
    biz: dict = Depends(_require_business),
    bot_name:       str  = Form(default="Quiribot"),
    greeting:       str  = Form(default="Hi! How can I help?"),
    primary_color:  str  = Form(default="#6366f1"),
    button_color:   str  = Form(default="#6366f1"),
    position:       str  = Form(default="bottom-right"),
    tone:           str  = Form(default="friendly"),
    blocked_topics: str  = Form(default=""),
    avatar_visible: Optional[str] = Form(default=None),
):
    cfg = {
        "bot_name":       bot_name,
        "greeting":       greeting,
        "primary_color":  primary_color,
        "button_color":   button_color,
        "position":       position,
        "tone":           tone,
        "blocked_topics": blocked_topics,
        "avatar_visible": avatar_visible == "on",
    }
    pdb.update_widget_config(biz["id"], cfg)

    # Re-fetch biz and cfg to render updated preview
    updated_biz = dict(pdb.get_business_by_id(biz["id"]))
    return templates.TemplateResponse(
        "business_customize.html",
        {"request": request, "business": updated_biz, "cfg": cfg, "success": True},
    )


# ---------------------------------------------------------------------------
# Embed snippet page
# ---------------------------------------------------------------------------

@router.get("/snippet", response_class=HTMLResponse)
async def business_snippet(
    request: Request,
    biz: dict = Depends(_require_business),
):
    return templates.TemplateResponse(
        "business_snippet.html",
        {"request": request, "business": biz},
    )
