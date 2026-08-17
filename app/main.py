"""
Entrypoint — Restaurant AI Agent (MVP v0.1 skeleton, Days 1-2).

Structure: the telephony provider (Twilio today) and the CallHandler
(echo today) are fully independent of each other — see
app/telephony/base.py for details.

Definition of Done for this phase:
Call the number, the call reaches the backend, and you hear an echo of
your voice.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.echo_handler import EchoCallHandler
from app.api import restaurants
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import engine
from app.telephony.twilio_provider import build_router as build_twilio_router

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Note: create_all is only suitable for local development/early MVP.
    # Once there's real data, switch to Alembic migrations (Days 11-12).
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Current CallHandler: simple echo (Phase 1). Will be replaced with a real
# agent in Phase 2+ without any change to the telephony layer.
call_handler = EchoCallHandler()

app.include_router(build_twilio_router(call_handler))
app.include_router(restaurants.router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
