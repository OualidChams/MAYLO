"""
Stopgap protection for internal/admin endpoints (Phase 1).

This is deliberately NOT the authorization model from ROADMAP.md section 4
(Actor / Membership / Permission / SecurityContext / Audit event) — there
are no real human actors to authorize yet (no dashboard, no login). Building
that now would be weeks of work with no current payoff.

What this IS: a single shared secret that closes the actual, immediate,
zero-effort-to-exploit gap — these endpoints sit on a public Railway/ngrok
URL as soon as the server is deployed, and until now had no protection at
all (anyone could GET /restaurants and read every restaurant in the DB).

Replace this with the real per-actor authorization model in Phase 12, once
there's an actual identity/membership system to check against.
"""
from fastapi import Header, HTTPException

from app.core.config import get_settings


async def require_admin_key(x_admin_key: str = Header(...)) -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        # Fail closed: an unconfigured key means "not set up", not "open by
        # default". Generate one with e.g. `openssl rand -hex 32` and set
        # ADMIN_API_KEY in .env / Railway variables.
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY is not configured on the server")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
