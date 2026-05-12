"""
Owner admin router — mounts at /owner
All routes require session cookie (owner_session=<signed token>).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from portal.auth import verify_owner, create_access_token, decode_access_token
from portal import db as pdb

router    = APIRouter(prefix="/owner")
templates = Jinja2Templates(directory="portal/templates")

_SESSION_COOKIE = "qb_owner_session"


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

def _require_owner(request: Request) -> bool:
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=307, headers={"Location": "/owner/login"})
    payload = decode_access_token(token)
    if not payload or payload.get("role") != "owner":
        raise HTTPException(status_code=307, headers={"Location": "/owner/login"})
    return True


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def owner_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="owner_login.html", context={"error": None})


@router.post("/login")
async def owner_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    if not verify_owner(username, password):
        return templates.TemplateResponse(
            request=request,
            name="owner_login.html",
            context={"error": "Invalid credentials."},
            status_code=401,
        )
    token = create_access_token("owner", extra={"role": "owner"})
    resp  = RedirectResponse("/owner/dashboard", status_code=303)
    resp.set_cookie(_SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=86400)
    return resp


@router.get("/logout")
async def owner_logout():
    resp = RedirectResponse("/owner/login", status_code=303)
    resp.delete_cookie(_SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
async def owner_dashboard(
    request: Request,
    status: str = "all",
    _auth: bool = Depends(_require_owner),
):
    all_businesses = pdb.list_businesses()
    if status != "all":
        filtered = [b for b in all_businesses if b.status == status]
    else:
        filtered = all_businesses

    return templates.TemplateResponse(
        request=request,
        name="owner_dashboard.html",
        context={
            "businesses":    filtered,
            "status":        status,
            "total":         len(all_businesses),
            "pending_count": sum(1 for b in all_businesses if b.status == "pending"),
            "active_count":  sum(1 for b in all_businesses if b.status == "active"),
        },
    )


# ---------------------------------------------------------------------------
# Business detail view
# ---------------------------------------------------------------------------

@router.get("/business/{business_id}", response_class=HTMLResponse)
async def owner_business_detail(
    request: Request,
    business_id: str,
    _auth: bool = Depends(_require_owner),
):
    biz = pdb.get_business_by_id(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return templates.TemplateResponse(
        request=request,
        name="owner_business.html",
        context={"business": biz},
    )


# ---------------------------------------------------------------------------
# Actions: approve / reject / suspend
# ---------------------------------------------------------------------------

@router.post("/business/{business_id}/approve")
async def owner_approve(
    business_id: str,
    _auth: bool = Depends(_require_owner),
):
    pdb.update_business_status(business_id, "active")
    return RedirectResponse(f"/owner/business/{business_id}", status_code=303)


@router.post("/business/{business_id}/reject")
async def owner_reject(
    business_id: str,
    reason: str = Form(default="Application did not meet requirements."),
    _auth: bool = Depends(_require_owner),
):
    pdb.update_business_status(business_id, "rejected", reason=reason)
    return RedirectResponse(f"/owner/business/{business_id}", status_code=303)


@router.post("/business/{business_id}/suspend")
async def owner_suspend(
    business_id: str,
    _auth: bool = Depends(_require_owner),
):
    pdb.update_business_status(business_id, "suspended")
    return RedirectResponse(f"/owner/business/{business_id}", status_code=303)
