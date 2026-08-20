# Restaurant AI Voice Agent — Roadmap & Decisions

Single reference instead of digging through chat history. Update this
whenever a real decision changes.

---

## 1. Current Stack

| Layer | Decision | Status |
|---|---|---|
| Telephony | Twilio | Behind a `CallHandler` abstraction — see `app/telephony/base.py` |
| STT | Deepgram Flux | API, self-hosting deferred (Phase 15) |
| LLM | Qwen3.6-35B-A3B | API via Alibaba Model Studio, self-hosting deferred (Phase 15) |
| TTS | Fish Audio S2.1 Pro | API, self-hosting deferred (Phase 15) |
| Backend | Python / FastAPI async | Modular monolith |
| DB | PostgreSQL / Supabase | Direct SQLAlchemy (not supabase-py) — keeps leaving Supabase easy if ever needed |
| Deploy | Railway | |
| Monitoring | Sentry | Starts Phase 11-12 |

**Golden rule:** every provider is replaceable. The domain layer (restaurant,
orders, agent) belongs only to us.

**Priority order (why every "defer this" decision above gets made):**
PMF → unit economics → capital efficiency → timing → technology. Per CB
Insights' analysis of 385 VC-backed shutdowns since 2023: poor
product-market fit (43%) and unsustainable unit economics (19%) are the
actual causes; "ran out of capital" (70%) is almost always the downstream
symptom. Technical/technology issues: 5%. This is *why* RBAC, Temporal,
Go, CI/CD, and staging environments all stay deferred — not because
they're bad ideas, but because none of them address the two things that
actually kill a project at this stage. The question that matters right
now is "will a real restaurant pay for this," not "is the architecture
enterprise-ready."

**Backend language:** Python-first, measurement-driven, performance-critical
components replaceable. Python isn't the RAM/CPU bottleneck here — the
workload is I/O-bound orchestration (await Deepgram/Qwen/Fish Audio), which
async Python handles well, and the AI/eval/RAG ecosystem is a real advantage
while the product is still being discovered. If a real bottleneck ever
shows up (measured, not guessed), the fix is replacing *that component*
behind its existing boundary (e.g. `CallHandler`) — Go first (best
performance/complexity trade-off for networking/WebSocket-heavy work),
Rust only if a specific case (DSP/audio processing) truly needs it. No
rewrite planned or needed now.

---

## 2. Phase Plan

Phase numbers are deliberately stable — refine acceptance criteria in
place, don't renumber for a new framing. (Noting this because more than
one review has proposed reshuffling phases into new names for work that's
already captured under an existing one — see Phase 6 note below for an
example. Renumbering has a real cost: it makes this file stop being a
reliable "already decided" reference.)

- ✅ **Phase 1 — Walking Skeleton** (done): Twilio → Media Stream WebSocket
  → echo. `CallHandler`/`TwilioProvider` separated from day one.
- **Phase 2 — Hearing**: Deepgram streaming STT instead of the echo. Measure
  time-to-first-transcript from the start. 🆕 **Added:** basic per-call
  tracing starts here too, not deferred to Sentry in Phase 11-12 — just
  structured log lines per component (`stt.first_transcript`,
  `stt.final_transcript`, timings), cheap now, expensive to reconstruct
  retroactively once real calls are flowing. 🆕 **Acceptance criterion:**
  every transcript event (interim and final) is scoped to `call_id` +
  `restaurant_id` — never a bare/global transcript stream. Already
  structurally guaranteed by `CallHandler.on_audio(call_id, ...)`; stating
  it explicitly so it stays true as Deepgram's interim/final distinction
  and timestamps get added. 🆕 **Trace identity, introduced incrementally
  Phase 2→6, not built now:** `Call` already exists; as Phase 2/3/6 land,
  each needs to produce a `Turn` (STT+LLM+tool calls+TTS for one
  back-and-forth) and each tool call needs a `ToolExecution` record —
  this is the forensic trail for "why did the AI say/charge that." Not
  schemed in detail now because the exact shape depends on what Phase 2's
  STT output and Phase 6's tool-call format actually look like — guessing
  the columns before either exists risks the same wrong-schema problem
  Organization avoided by being genuinely stable already. Also extend the
  event vocabulary from `stt.first_transcript` etc. to include
  `agent.tool.requested/authorized/rejected/executed/failed` and
  `order.created/cancelled` once there's an agent and tools to emit them.
- **Phase 3 — Brain**: Qwen. 🆕 **Acceptance criterion:** streaming tokens →
  TTS directly from the first implementation, not a later retrofit. Goal: no
  waiting for the full response before audio starts. 🆕 **Added — loop stop
  conditions** (the agent's think→act→observe loop must have explicit
  limits, not run until "done"): max tool calls per turn, max turn duration,
  stop on order confirmed, stop on auth failure, stop when human approval
  is required. 🆕 **Added — memory categories**, explicit from the start:
  short-term (this conversation/current order), long-term (restaurant/
  customer preferences), system state (order status, payment status —
  always DB-backed, never LLM-recalled; same "LLM never owns truth"
  principle already applied to price/availability). 🆕 **`LLMProvider`
  interface shaped as a router, not just a switch:** built to dispatch
  per-request (simple intent → small/local model, complex reasoning →
  Qwen), not only to swap one provider for another wholesale. Costs
  nothing extra to design this way now; retrofitting routing onto
  single-provider-per-turn code later would.
- **Phase 4 — Stage Contracts**: Reception/Order/Reservation as separate
  stages (input/context/tools/rules/output/failure for each) — principle
  from the ICM paper, without filesystem-as-runtime.
- **Phase 5 — DB**: effectively done as part of Phase 1 (`app/db/models.py`)
  — restaurants/menu/orders/calls with `restaurant_id` from day one.
- **Phase 6 — Tools**: 7 core tools. 🆕 **Added:** Redis cache for
  menu/hours/config (data that repeats and rarely changes) — Postgres
  remains the source of truth. **Reaffirmed, not a separate phase:** each
  tool is a thin wrapper over an Application Service
  (`OrderService.create_order()` etc., already noted in section 4) — built
  *with* the tool that first needs it, not scaffolded speculatively ahead
  of time for services nothing calls yet (`ReservationService`,
  `MenuService`... only when Phase 6 actually needs them). 🆕
  **Pre-requisite, not a Phase 12 concern:** every tool receives a
  minimal `SecurityContext` (`actor_type="ai_agent"`, `actor_id`,
  `restaurant_id`, `capabilities: set[str]`) built by the call session,
  not by the tool guessing. This is a stable value object — its shape is
  already fully determined by decisions already made (Organization/
  Restaurant hierarchy, the least-privilege-agent principle) — unlike
  `OrderService`, it doesn't need Phase 6's tools to exist first to know
  its fields. Still not implemented as code yet, since nothing calls it
  until Phase 6 tools exist to receive it, but tools must be built
  against this shape from their first line, not retrofitted onto it —
  that's the actual lesson from the review that raised this. When human
  actors arrive in Phase 12, they populate the same `SecurityContext`
  shape via membership/role — the interface doesn't change, only what
  constructs it. 🆕 **Menu truth stays server-side:** tool arguments
  reference `menu_item_id`/`modifier_id`, never a full item structure
  (`{"name": ..., "price": ...}`) invented by the model — the backend
  resolves IDs into truth, same principle as price/availability already
  in this file.
- **Phase 7 — Order Safety**: draft → validate → confirm → submit. The LLM
  never owns the truth for prices/availability. 🆕 **Added — risk-based
  human-in-the-loop:** not everything auto-executes just because validation
  passed. Threshold-based approval (e.g. a large refund or an order above
  a configurable amount needs human confirmation; a normal order doesn't) —
  same shape as the existing Human Handoff path, just triggered by risk
  level instead of only by the agent being stuck.
- **Phase 8 — Voice Out**: Fish Audio streaming + barge-in. 🆕 **Same
  requirement as Phase 3:** streaming from the start, target TTFA P50
  <700ms / P95 <1.2s.
- **Phase 9 — First Real Restaurant**: ~100 calls, classify every failure.
  🆕 **Added:** per-call cost telemetry (STT minutes, LLM tokens, TTS
  characters) — this turns the economics tables in section 3 from guesses
  into real numbers. 🆕 **Also added:** basic process resource metrics
  (RAM, CPU, event-loop latency) captured from day one of the pilot — so
  the Python vs. Go/Rust question (section 1) is ever settled by data,
  not guesswork, if it comes up again. 🆕 **The actual acceptance
  criterion that matters most:** would this restaurant pay €X/month for
  this, unprompted — not "did the demo work." PMF and unit economics
  (section 1) get measured here first, before any further technical
  investment beyond this phase. 🆕 **Cost metric sharpened:** report
  cost/successful-call, not cost/call or cost/minute — a cheap call that
  fails and needs a human anyway is worse than a slightly pricier one
  that works, so the two numbers (telemetry + failure classification,
  both already tracked above) get combined into the one that actually
  matters.
- **Phase 10 — Evaluation System**: eval-case dataset, compare
  models/prompts. 🆕 **Refined:** test full trajectories (which tools were
  called, in what order, with what arguments), not just whether the final
  answer looks right — an agent can reach a correct-looking answer through
  a wrong/unsafe path, and that has to fail the eval too. 🆕 **Seed dataset
  written now, as a paper exercise (`eval_cases/`, 19 hand-written golden
  cases across ordering/authorization/tool_use/adversarial/recovery)** —
  see `eval_cases/README.md` for the schema and the "evaluate contracts,
  not implementation details" principle. This exists before the agent
  does; Phase 10 wires an automated runner up to it once tools (Phase 6)
  and the agent loop (Phase 3) exist. Extend toward 25-30 using real
  Phase 9 failures once they exist, not more paper exercise. 🆕
  **Runner harness built now too (`evals/`), tested against hand-built
  trajectories:** loads `eval_cases/`, captures a `Trajectory`
  (interpretation, tool calls, final response), and grades it in two
  honest tiers — `grade_structural()` is real and automated today
  (catches restaurant_id scope leaks and forbidden-phrase responses
  deterministically, no model needed); `judge_with_llm()` is a documented,
  deliberately unimplemented extension point for the natural-language
  contracts, left that way until Phase 3/6 produce real trajectories
  worth spending judge-model calls on. Run it: `python -m evals.run`.
- **Phase 11 — RAG**: only after the MVP is proven. Stage-aware retrieval
  (not dumping everything).
- **Phase 12 — Dashboard**: calls/orders/failed calls. Note: Supabase Auth
  here = highest migration risk if used — a conscious decision if it happens.
  🆕 **Noted for later, not scoped yet:** if/when there's a CEO view and an
  internal engineering view in addition to the restaurant's own dashboard,
  they should be projections of the same domain model, not three separate
  systems — same principle as the Application Service layer serving REST/
  voice/MCP. Don't design the actual UX now; let Phase 9 pilot feedback
  shape what restaurant owners actually ask for first.
- **Phase 13 — Multi-tenant**: onboarding = "Keep Existing Number →
  Forwarding" is the default (confirmed by the telephony discussions),
  "Connect SIP/PBX" = a deferred advanced integration.
- **Phase 14 — Reliability**: timeouts/retries/circuit breakers/LLM router
  (fallback provider). 🆕 **Noted for whenever a CI/CD pipeline exists
  (downstream of the git-repo setup, itself already deferred):** Phase 10
  evals should gate deployment, not just report scores — a new version can
  pass every unit test while the agent gets measurably worse (lower order
  accuracy, more unsafe trajectories), and only a staging eval run catches
  that. Nothing to build now; there's no repo or pipeline yet for this to
  attach to.
- **Phase 15 — Self-hosting**: 🆕 **Trigger now defined:** after real Phase 9
  data + a restaurant count that justifies GPU capex, redo the Architecture
  A/B/C/D comparison **with actually measured numbers**, not published
  vendor rates (we saw a large gap between a marketing claim from Telnyx
  and an independent real-world measurement).

---

## 3. Latency & Economics Targets (for later reference)

**TTFA (Time To First Audio) — from the end of the customer's speech to the
start of the AI's audio:**

| Level | TTFA |
|---|---|
| Excellent | <700ms (P50) |
| Production target | <1.2s (P95) |

⚠️ Measure from the **actual call recording** (mic → speaker), not internal
timestamps — the gap can be as much as half a second.

**Architecture C (hybrid) — economic target at 150 restaurants / 750k
minutes/month:**
COGS target €0.010–0.018/min → 40–60% gross margin. Self-host Qwen only at
first (STT/TTS stay managed until 500-1,000+ clients).

---

## 4. Authorization & Multi-tenancy

Full model (for later reference, NOT built yet): `Platform → Organization →
Restaurant`, with `users` / `organization_memberships` / `restaurant_memberships`
kept separate from identity, RBAC (roles = bundles of permissions, not
hardcoded role checks), an `Actor → Action → Resource → Scope` authorization
model, a Security Context per request, append-only audit events, and
"fail closed" as a hard rule. Applies to human actors AND the AI agent
itself — the agent is a constrained actor (e.g. `order.create`,
`menu.read`), never a trusted admin; it *requests* a capability, the
backend *grants* it — same principle as "the LLM never owns price/
availability truth," just generalized.

**Built now (cheap on an empty DB, expensive to retrofit later):**
`Organization` entity added as the tenant boundary above `Restaurant`
(`app/db/models.py`). No RBAC/permissions/audit/security-context — those
need real human actors to exist first.

**Deferred to Phase 12 (Dashboard), trigger = real human users/login exist:**
users/memberships tables, roles→permissions, policy engine, Security
Context middleware, audit-event log, Row-Level Security, break-glass
access, sensitivity classes for call recordings/transcripts.

**🆕 Added to Phase 6 (Tools) acceptance criteria:** every tool is scoped
to a single `restaurant_id` taken from the call session — never trusted
from LLM free text. The LLM requests a tool call; the tool itself decides
whether it's allowed and valid. No tool gets raw/unscoped DB access.

**🆕 Reviewed against the actual code, decision made:** the review correctly
found `/restaurants` endpoints fully open on what will be a public
Railway/ngrok URL — real, zero-effort-to-exploit gap. Fixed now with a
single shared-secret dependency (`app/core/security.py`,
`require_admin_key`, fail-closed if unconfigured) — NOT the full
Actor/Membership/Permission/SecurityContext/Audit foundation the review
proposed building before Phase 2. Reasoning for not building the full
thing yet: it needs real human actors to check against, and none exist
(no dashboard, no login) — so most of it has no payoff to validate against
right now and would just be guessed at, same trap as premature self-hosting
in section 5. The shared secret closes the actual exposure at ~15 minutes
of cost instead of days.

**Also noted, not yet acted on:** Twilio webhook signature validation
(`X-Twilio-Signature`, via `twilio.request_validator.RequestValidator`) is
a real gap on `/twilio/voice` and `/twilio/status` — anyone who finds the
URL can POST fake call events. Deliberately NOT added yet: getting the
callback URL right behind ngrok/Railway's reverse proxy (scheme headers)
is easy to get subtly wrong, and Phase 1's actual echo flow hasn't been
verified end-to-end on a real call yet — better to add this once that's
confirmed working, so a signature-validation bug doesn't get confused with
a Phase 1 bug. Do this before Phase 9 (real pilot) at the latest.

**Design principles captured for later (no code yet — nothing exists to
apply them to):**
- *Application Service layer* (Phase 6/7): `OrderService.create_order()`
  etc. between the API/agent-tool layer and the DB, so REST, voice tools,
  and any future MCP adapter share one implementation instead of drifting.
- *Actor concept*: informally, "who's calling a tool" is `AI_AGENT` scoped
  to `restaurant_id` for now — no `Actor` class hierarchy until Phase 12
  needs to distinguish it from `HumanUser`/`PlatformEmployee`.
- *MCP*: if ever added, it's a thin adapter over the same domain/tools —
  never where authorization or business logic lives.

---

## 5. Deliberately Deferred + Trigger to Revisit

| Decision | Deferred to | Trigger |
|---|---|---|
| Self-hosting STT/LLM/TTS | Phase 15 | Real Phase 9 data + scale that justifies GPU |
| Telnyx SIP/BYOC | After Phase 15 (if needed) | Twilio proves genuinely insufficient economically |
| Connect existing PBX/SIP | Advanced integration | Not part of MVP or even Phase 13 |
| RAG / pgvector | Phase 11 | After the MVP is proven |
| Kubernetes / Kafka / microservices | Not planned | No need at this scale |
| Full RBAC/authz engine, audit log, RLS, break-glass access | Phase 12 | Real human dashboard users/login exist |
| Outbound calling | Not in scope in any current phase | If ever added: agent requests `call_customer()`, backend authorizes (actor/restaurant/customer/caller-ID/audit checks) before it reaches `CallHandler` — never direct SIP/provider access from the agent |
| Workflow orchestration (Temporal leaning; Conductor/Orkes, n8n considered) | Phase 12/13 | Real async multi-step process exists: onboarding, billing/usage aggregation, or POS sync. Never for the live call path — that stays a single async Python request. |
