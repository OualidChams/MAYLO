# Eval Cases — Phase 10 Seed Dataset

Hand-written golden dataset per ROADMAP.md Phase 10. This is the seed
(~20 cases) the automated evaluation framework gets built from once the
agent (Phase 3+) and tools (Phase 6) exist — written now as a paper
exercise so it's ready rather than designed from scratch later.

## The one rule every case follows

**Evaluate contracts, not implementation details.**

Wrong: "the agent must call `check_menu()` exactly once."
Right: "the agent must establish the menu item and its current
authoritative price before creating an order."

The wrong version breaks the day a tool gets renamed or split in two.
The right version survives changes to tools, prompts, and models — it's
checking the business requirement, not today's code shape. Every
`tool_trajectory_contract` entry below is written this way on purpose.

## Why trajectory, not just final answer

Two agents can produce the identical final sentence to the customer —
"Your order is two large pizzas, one without cheese" — while one of them
got there by inventing a price and only fixing it after the backend
rejected it. Same output, very different reliability. A case only passes
if the *path* satisfies every contract, not just the last message.

## Schema

```yaml
id:                     # unique, stable — used for regression tracking
category:               # matches the folder path
primary_failure_class:  # the ONE failure mode this case is designed to catch
description:            # one line, human-readable

input:
  transcript:            # the conversation as the customer would say it
  context:                # any setup assumptions (menu state, existing order, actor)

expected_interpretation: # what the agent should extract/understand
  intent:
  entities:

tool_trajectory_contract: # business requirements the tool-call path must satisfy
  - ...

forbidden:                # things that must NEVER happen, regardless of final answer
  - ...

expected_state_changes:   # DB/domain effects, if any
  - ...

expected_final_response:
  must_include: [...]
  must_not_include: [...]

fail_if:                  # explicit, checkable failure conditions
  - ...
```

## Failure taxonomy (from ROADMAP.md Phase 10)

Interpretation · Tool selection · Tool order · Arguments · Authorization ·
Business logic · State mutation · Safety · Final response · Hallucination
· Recovery

Each case's `primary_failure_class` maps to one of these. The full
dataset should eventually cover all of them more than once — this seed
set covers each at least once.

## Categories in this seed set

- `ordering/` (7 cases) — the core product surface
- `authorization/` (3 cases) — tenant/scope isolation
- `tool_use/` (3 cases) — mechanical correctness of tool calls
- `adversarial/` (3 cases) — the agent under active manipulation
- `recovery/` (3 cases) — external failures (timeouts, bad tool results)

19 cases total. Extend toward 25-30 as real Phase 9 call failures surface
new scenarios worth encoding — the real pilot data is a better source of
new cases than more paper exercise.
