"""
Redirects the app's real pages to /setup until the initial (real, DB-backed)
SuperAdmin account exists. Registered once from main.py via
app.add_middleware() - the pattern nicegui_llms.md documents for exactly
this kind of cross-cutting request handling (auth, redirects, etc.).

Only the routes in GATED_ROUTES are checked - NiceGUI's own internal routes
(websocket, static assets, etc.) and the setup/register/auth routes
themselves are left alone, so the wizard (and Discord's OAuth redirect back
into it) always works even before an account exists.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.components.layout import NAV_ITEMS
from app.data.accounts import has_any_account

GATED_ROUTES = {"/", *(route for route, *_ in NAV_ITEMS)}


class SetupGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in GATED_ROUTES and not await has_any_account():
            return RedirectResponse("/setup")
        return await call_next(request)
