# Building a Reliable Agent

General principles, each tied to where it actually lives (or doesn't yet)
in this project. Written because "how do you build a reliable agent" is
a real, standalone question worth a straight answer — not just a pointer
back into ROADMAP.md.

## 1. Separate the model from the truth

The single most important rule. The LLM proposes; a deterministic backend
disposes. Price, availability, permissions, order state, payment state —
none of it is ever something the model "remembers" or invents. It calls a
tool, the tool returns authoritative data, the model relays it.

**In this project:** `OrderItem` stores price at order time rather than
trusting `MenuItem.price` later. Phase 6/7 tools are the enforcement
point — `eval_cases/ordering/simple_order.yaml` fails if a price appears
in the final response that didn't come from a tool call.

## 2. Constrain the loop

An agent's think→act→observe cycle needs explicit termination, not
`while True`. Max tool calls per turn, max turn duration, stop on
confirmed/failed/approval-needed. Without this, a confused model can spin
indefinitely or take actions in a state where it should have stopped.

**In this project:** Phase 3 acceptance criteria (`ROADMAP.md` section 2).
`eval_cases/recovery/tool_timeout.yaml` specifically checks the bound is
respected, not just that recovery happens eventually.

## 3. Narrow tools that validate themselves

Small, specific tools (`create_order`, not `execute_sql`), each carrying
its own authorization and business-rule checks inside it — never trusting
that the model already checked. The model requests a capability; the tool
decides if it's actually allowed, right now, for this data.

**In this project:** Phase 6's criterion that every tool is scoped to
`restaurant_id` from the call session, never from LLM-parsed text.
`eval_cases/authorization/wrong_restaurant_scope.yaml` is the regression
test for exactly this.

## 4. Context discipline

Give the model what the current stage needs, not the whole database.
More context isn't more reliable — it's more surface area for the model
to latch onto the wrong thing.

**In this project:** the Stage Contract discussion (input/context/tools/
rules/output/failure per stage), Phase 4.

## 5. Human-in-the-loop, scaled by risk

Not everything should auto-execute just because validation passed. Small,
reversible actions: automatic. Large or irreversible ones: a human
confirms first. The threshold is configurable, not hardcoded per-feature.

**In this project:** Phase 7's risk-based HITL criterion.
`eval_cases/ordering/high_value_refund_requires_approval.yaml`.

## 6. Evaluate trajectories, not outputs

Two agents can produce an identical final sentence while one of them got
there by inventing a price and only correcting it after a rejection. Same
output, different reliability. Grade the path, not just the last message.

**In this project:** Phase 10, and the 19-case seed dataset in
`eval_cases/` built specifically around this principle.

## 7. Observability that survives "why did this fail?"

When a customer asks why their order didn't reach the kitchen, "the AI
probably made a mistake" isn't an answer. Every call needs a trace: which
tools were called, with what arguments, what each returned, how long each
step took, and why the agent stopped when it did.

**In this project:** per-call tracing pulled forward to Phase 2 (not
deferred to Sentry at Phase 11-12), `call_id`/`restaurant_id` scoping on
every event.

## 8. Latency is a reliability dimension, not a separate concern

For voice specifically, a technically correct answer delivered two
seconds late has already failed the interaction — the customer either
hung up or started talking over it. Streaming isn't a nice-to-have
retrofit; it has to be designed in from the first implementation.

**In this project:** TTFA targets (P50 <700ms, P95 <1.2s) measured from
actual call audio, not internal timestamps; streaming required from
Phase 3/8's first implementation.

## 9. Idempotency and safe retries for anything external — gap, not yet built

Payment charges, POS submissions, SMS confirmations — any call to an
external system needs to be safe to retry without double-charging or
double-submitting. This is genuinely not addressed yet in this project;
it's Phase 14 (Reliability) territory and hasn't been designed even on
paper. Worth flagging honestly rather than implying it's covered:
whenever Phase 6/7 starts touching payment or POS integration, this needs
real design, not an afterthought.

## 10. Test adversarially, not just for happy paths

Voice input is untrusted text the moment it's transcribed. Prompt
injection, conflicting instructions, social-engineering-style requests
("I'm calling for the owner") — these need explicit test cases, not an
assumption that a well-behaved customer is the only customer.

**In this project:** `eval_cases/adversarial/` (3 cases).

## 11. Fail honest, not fail silent

When a tool times out or returns something inconsistent, the correct
response is "I'm having trouble looking that up" — never a confident,
invented answer to fill the gap. An agent that's occasionally slow is
recoverable. An agent that occasionally lies convincingly is not.

**In this project:** `eval_cases/recovery/` (3 cases), all built around
this exact distinction.

## 12. A golden eval set is necessary but not sufficient

19 hand-written cases catch known failure modes. Real customers will find
new ones the dataset never anticipated. Production monitoring — tracking
task success rate, escalation rate, correction rate on *real* calls — is
what catches drift the eval set can't.

**In this project:** Phase 9's per-call telemetry and failure
classification is this monitoring layer; the eval set and the pilot
telemetry are meant to feed each other (new pilot failures become new
eval cases, per `eval_cases/README.md`).

## 13. Start narrow, expand only when evidence demands it

One agent with tools before a planner/multi-agent swarm. One pilot
restaurant before ten. Local complexity added only when a stage's own
evals show it's actually needed — not because a more sophisticated
architecture is available.

**In this project:** this is the throughline of the whole `ROADMAP.md` —
every deferred item (RBAC, Temporal, Go, self-hosting) is deferred
because reliability here is currently better served by depth on the
narrow path than breadth across more of them.

---

None of this is exotic. It's the same handful of ideas applied
consistently: **don't trust the model with truth, bound what it can do,
watch what it actually did, and fail honestly when something breaks.**
Everything else is detail.
