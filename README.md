# Restaurant AI Agent — Phase 1 "Walking Skeleton" (Days 1-2)

**Definition of Done for this phase:**
Call the Twilio number → hear a short greeting → the call connects to a
bidirectional Media Stream WebSocket → **everything you say is echoed
back to you immediately**. This proves the full path is sound:
`Twilio → FastAPI → Twilio → caller`.

In the logs you should see, in order: `call_started` → `audio_connected` →
(while talking) → `call_ended`.

Not yet included: real Deepgram STT, Qwen, Fish Audio TTS — these start in
Phase 2 (Days 3-4), where the echo will be replaced by sending audio to
Deepgram.

---

## 1. Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# open .env and fill in DATABASE_URL, and generate a value for ADMIN_API_KEY:
#   openssl rand -hex 32
```

### Database (Supabase)
1. Create a new project at [supabase.com](https://supabase.com)
2. From **Project Settings → Database → Connection string**, copy the URI
3. Replace `postgresql://` with `postgresql+asyncpg://` and put it in `DATABASE_URL`

### Run the server
```bash
uvicorn app.main:app --reload --port 8000
```
Open `http://localhost:8000/health` — you should see `{"status": "ok", ...}`.
On first run in `development` mode, all tables are created automatically.

---

## 2. Expose the server to the internet (to test Twilio locally)

Twilio needs a public URL to reach your machine. Use ngrok:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL — you'll need it next.

(In production you won't need ngrok — Railway gives you a public domain
directly, see section 5.)

---

## 3. Configure your Twilio number

1. From [Twilio Console](https://console.twilio.com), buy a number (Phone Numbers → Buy a number)
2. Open the number's settings → **Voice Configuration** section
3. Under "A call comes in": choose **Webhook**, and paste:
   `https://xxxx.ngrok-free.app/twilio/voice` (or your Railway domain later) — Method: `HTTP POST`
4. (Optional for now) Status Callback URL: `https://xxxx.ngrok-free.app/twilio/status`
5. Save

---

## 4. Register a test restaurant and link it to the number

`phone_number` must match the Twilio number **exactly** in E.164 format
(e.g. `+14155551234`):

```bash
curl -X POST http://localhost:8000/restaurants \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <your ADMIN_API_KEY from .env>" \
  -d '{
        "name": "Test Pizzeria",
        "phone_number": "+14155551234",
        "timezone": "America/Los_Angeles",
        "language": "en"
      }'
```

Now call the Twilio number from your phone.
You should hear: *"Hello! Connecting you to Test Pizzeria."* — then say
anything — you should hear your own voice echoed back immediately.

Watch the uvicorn logs during the call — you should see, in order:
```
call_started call_sid=CA... restaurant=Test Pizzeria
voice.connected
audio_connected call_sid=CA... stream_sid=MZ...
call_ended call_sid=CA... stream_sid=MZ...
```

You'll also find a new row in the `calls` table in Supabase (Table Editor).

✅ If you heard the echo and saw these logs — **Phase 1 (Days 1-2) is done.**

---

## 5. Deploy to Railway (optional now, required before the pilot)

1. Connect the repo to [Railway](https://railway.app)
2. Add the same environment variables as your `.env` (Railway → Variables)
3. Railway will auto-detect `requirements.txt` and run uvicorn
4. Use Railway's assigned domain instead of the ngrok URL in your Twilio settings

---

## Project structure

```
app/
├── main.py              # entrypoint + lifespan (creates tables in dev)
├── core/config.py        # settings (env vars)
├── db/
│   ├── models.py          # Restaurant, Location, MenuItem, OpeningHours, Call, Order, OrderItem
│   └── session.py         # async Postgres connection
├── telephony/
│   ├── base.py             # CallHandler — the general interface, carrier-agnostic
│   └── twilio_provider.py  # the only implementation of that interface today (Twilio TwiML + Media Streams)
├── agent/
│   └── echo_handler.py     # current CallHandler: echo only (Phase 2+ replaces it with a real agent)
└── api/
    └── restaurants.py      # simple restaurant CRUD
```

## Why this structure?

`app/telephony` is the only place in the project that "knows" Twilio-specific
details (TwiML, the Media Streams JSON protocol). Everything else — the DB,
the agent, tools later on — only talks to `CallHandler` (raw audio bytes +
3 events: started/audio/ended).

This means adding Telnyx SIP/BYOC later (after Phase 15, once it's
economically justified) only requires writing a new
`app/telephony/telnyx_provider.py` — without touching anything else in the
project. We deliberately did NOT build a `TelnyxProvider` now: building a
"unified" interface before a second real implementation exists is usually
guessed wrong and gets rewritten anyway.

## Next step: Phase 2 — Hearing (Days 3-4)

Replace the echo logic in `app/agent/echo_handler.py` with sending each
`media` payload to Deepgram streaming STT (instead of echoing it back),
printing the transcript in real time in the logs. See the "Phase 2 —
Hearing" section of ROADMAP.md for details (time-to-first-transcript,
interruptions, multi-language support).
