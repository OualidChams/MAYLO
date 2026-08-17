"""
Twilio as **one implementation** of the telephony interface (see
app/telephony/base.py) — not the call logic itself. This is the only
file in the project that knows Twilio-specific details: TwiML, and the
Media Streams protocol (JSON over WebSocket).

When Telnyx SIP/BYOC is added later: write a new
app/telephony/telnyx_provider.py in the same shape (a factory returning
a router), without touching CallHandler or anything in app/agent or app/db.
"""
import base64
import json
import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import VoiceResponse

from app.db.models import Call, Restaurant
from app.db.session import get_db
from app.telephony.base import CallHandler

logger = logging.getLogger(__name__)


def build_router(call_handler: CallHandler) -> APIRouter:
    """
    Factory instead of a global router — so we can inject a CallHandler
    (EchoCallHandler today, a real agent later) without this file knowing
    anything about STT/Qwen/TTS.
    """
    router = APIRouter(tags=["telephony:twilio"])

    def _twiml(vr: VoiceResponse) -> Response:
        return Response(content=str(vr), media_type="application/xml")

    def _stream_url(request: Request) -> str:
        host = request.headers.get("host") or request.url.hostname
        return f"wss://{host}/voice/stream"

    @router.post("/twilio/voice")
    async def incoming_call(
        request: Request,
        db: AsyncSession = Depends(get_db),
        CallSid: str = Form(...),
        From: str = Form(...),
        To: str = Form(...),
        CallStatus: str = Form("ringing"),
    ):
        result = await db.execute(select(Restaurant).where(Restaurant.phone_number == To))
        restaurant = result.scalar_one_or_none()
        vr = VoiceResponse()

        if restaurant is None:
            logger.warning("Inbound call to unregistered number: %s (CallSid=%s)", To, CallSid)
            vr.say("Sorry, this number is not configured yet.", voice="Polly.Joanna")
            vr.hangup()
            return _twiml(vr)

        if not restaurant.active:
            vr.say("Sorry, this restaurant is currently unavailable.", voice="Polly.Joanna")
            vr.hangup()
            return _twiml(vr)

        call = Call(
            restaurant_id=restaurant.id,
            twilio_call_sid=CallSid,
            from_number=From,
            status=CallStatus,
        )
        db.add(call)
        await db.commit()

        await call_handler.on_call_started(call_id=CallSid, restaurant_id=str(restaurant.id))

        vr.say(f"Hello! Connecting you to {restaurant.name}.", voice="Polly.Joanna")
        connect = vr.connect()
        connect.stream(url=_stream_url(request))
        return _twiml(vr)

    @router.post("/twilio/status")
    async def call_status(
        db: AsyncSession = Depends(get_db),
        CallSid: str = Form(...),
        CallStatus: str = Form(...),
    ):
        """Optional Status Callback — only updates the DB. CallHandler's
        lifecycle (on_call_ended) is driven by the WebSocket below since
        it's the faster/more accurate signal."""
        result = await db.execute(select(Call).where(Call.twilio_call_sid == CallSid))
        call = result.scalar_one_or_none()
        if call is None:
            logger.warning("Status callback for unknown CallSid=%s", CallSid)
            return {"ok": True}

        call.status = CallStatus
        if CallStatus in {"completed", "failed", "no-answer", "busy", "canceled"}:
            call.ended_at = datetime.now(timezone.utc)
        await db.commit()
        return {"ok": True}

    @router.websocket("/voice/stream")
    async def media_stream(websocket: WebSocket):
        await websocket.accept()
        call_sid: str | None = None
        stream_sid: str | None = None

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                event = msg.get("event")

                if event == "start":
                    start = msg["start"]
                    stream_sid = start["streamSid"]
                    call_sid = start["callSid"]
                    logger.info("audio_connected call_sid=%s stream_sid=%s", call_sid, stream_sid)

                elif event == "media":
                    # The only translation between Twilio's protocol (base64
                    # JSON) and the general CallHandler interface (raw bytes)
                    # happens here.
                    audio_in = base64.b64decode(msg["media"]["payload"])
                    audio_out = await call_handler.on_audio(call_id=call_sid, audio_chunk=audio_in)
                    if audio_out is not None:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": base64.b64encode(audio_out).decode()},
                                }
                            )
                        )

                elif event == "stop":
                    logger.info("call_ended call_sid=%s stream_sid=%s", call_sid, stream_sid)
                    if call_sid:
                        await call_handler.on_call_ended(call_id=call_sid)
                    break

        except WebSocketDisconnect:
            logger.info("call_ended (client disconnected) call_sid=%s", call_sid)
            if call_sid:
                await call_handler.on_call_ended(call_id=call_sid)

    return router
