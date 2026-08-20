"""
General interface for handling any call, fully decoupled from the
telephony provider.

Architecture decision: "Telnyx/Twilio = the road, we = the car and engine."
Any new telephony provider (TwilioProvider today, TelnyxProvider later)
only talks to CallHandler — it knows nothing about STT/Qwen/TTS.
The reverse is also true: CallHandler knows nothing about Twilio or
Telnyx or either one's JSON/SIP wire format — just raw audio bytes.

Deliberate note: there is no TelnyxProvider here yet. Building a
"unified" interface before a second real implementation (real Telnyx
SIP/BYOC) exists is risky — it's very likely to be guessed wrong. For
now we just make sure TwilioProvider is the sole implementation of this
interface, and that everything else in the app (DB, the future agent)
only talks to it — never to Twilio directly.
"""
from abc import ABC, abstractmethod


class CallHandler(ABC):
    @abstractmethod
    async def on_call_started(self, call_id: str, restaurant_id: str) -> None:
        """Called when the call starts (after the Call row is created in the DB)."""

    @abstractmethod
    async def on_audio(self, call_id: str, audio_chunk: bytes) -> bytes | None:
        """
        Inbound audio from the caller — raw PCM/mulaw (after the provider
        has decoded any encoding of its own, e.g. base64). Returns audio to
        send back to the caller directly (Phase 1: echo), or None if the
        response will arrive asynchronously later (Phase 2+: via streaming
        STT → Qwen → TTS).
        """

    @abstractmethod
    async def on_call_ended(self, call_id: str) -> None:
        """Called when the call ends."""
