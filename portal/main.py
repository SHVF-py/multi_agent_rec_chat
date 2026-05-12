"""
Portal main app — runs on port 7000.
Mounts:
  /owner/*    — Owner control panel (FastAPI router)
  /business/* — Merchant admin (FastAPI router)
  /widget/*   — Widget shell served as static HTML + JS

Run from project root:
  .venv/Scripts/python -m uvicorn portal.main:app --port 7000 --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from portal.owner.app    import router as owner_router
from portal.business.app import router as business_router

app = FastAPI(title="Quiribot Portal", docs_url=None, redoc_url=None)

# ---------------------------------------------------------------------------
# CORS — allow the widget iframe to call this server
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(owner_router)
app.include_router(business_router)

# ---------------------------------------------------------------------------
# Widget static files  (loader.js, chat.html, chat.js)
# ---------------------------------------------------------------------------
_WIDGET_DIR = Path(__file__).resolve().parent.parent / "widget"

# /widget/shell must be registered BEFORE the StaticFiles mount so it is
# matched first (Starlette checks routes in registration order).
@app.get("/widget/shell")
async def widget_shell():
    return FileResponse(str(_WIDGET_DIR / "chat.html"), media_type="text/html")

app.mount("/widget", StaticFiles(directory=str(_WIDGET_DIR)), name="widget")

# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return RedirectResponse("/business/login")
