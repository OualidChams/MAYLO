"""
Phase 1 (Days 1-2) — the simplest possible CallHandler: immediate echo,
proving the full audio path works regardless of which telephony provider
is used.

Phase 2+ will replace this file with a real agent (STT → Router → Qwen →
Tools → TTS), with no changes needed in app/telephony.
"""
import logging

from app.telephony.base import CallHandler

logger = logging.getLogger(__name__)


class EchoCallHandler(CallHandler):
    async def on_call_started(self, call_id: str, restaurant_id: str) -> None:
        logger.info("call_started call_id=%s restaurant_id=%s", call_id, restaurant_id)

    async def on_audio(self, call_id: str, audio_chunk: bytes) -> bytes | None:
        return audio_chunk  # direct echo — no STT, no Qwen, no TTS yet

    async def on_call_ended(self, call_id: str) -> None:
        logger.info("call_ended call_id=%s", call_id)
