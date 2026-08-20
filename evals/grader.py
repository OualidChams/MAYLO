"""
Grades a captured Trajectory against an EvalCase.

Two tiers, deliberately not blurred together:

1. Structural checks — deterministic, checkable from the Trajectory data
   alone, no model needed. These catch the single most important failure
   class in the whole project: restaurant_id scope leaks (see
   eval_cases/authorization/wrong_restaurant_scope.yaml).

2. Judged checks — the natural-language contracts (tool_trajectory_contract,
   forbidden, fail_if, expected_state_changes) require actual judgment
   about what happened and why ("was the menu item established via a
   menu-lookup tool before order creation?"). There's no honest way to
   automate that generically without either a hand-written checker per
   case or an LLM-as-judge pass. judge_with_llm() below is a real
   extension point, not a stub pretending to work — it's left
   unimplemented on purpose until there's an actual agent producing
   trajectories worth judging (Phase 3+). Building an LLM-judge harness
   with nothing real to test it against would be the same premature-
   infrastructure mistake this project has avoided everywhere else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from evals.models import EvalCase
from evals.trajectory import Trajectory


@dataclass
class GradeResult:
    case_id: str
    passed_structural: bool
    structural_failures: list[str] = field(default_factory=list)
    judged_checks_pending: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        status = "PASS (structural only)" if self.passed_structural else "FAIL"
        return f"[{status}] {self.case_id} — {len(self.judged_checks_pending)} judged checks still pending"


def grade_structural(case: EvalCase, trajectory: Trajectory) -> GradeResult:
    failures: list[str] = []

    # The single most important check in the project: restaurant_id scope.
    # Every tool call must carry the call session's own restaurant_id,
    # never one sourced from parsed customer speech.
    expected_restaurant_id = case.input_context.get("restaurant_id")
    if expected_restaurant_id:
        for call in trajectory.tool_calls:
            if call.restaurant_id is not None and call.restaurant_id != expected_restaurant_id:
                failures.append(
                    f"tool '{call.tool_name}' called with restaurant_id={call.restaurant_id!r}, "
                    f"expected {expected_restaurant_id!r}"
                )

    # Final response keyword checks — a weak proxy, not a substitute for
    # human/LLM review, but catches egregious misses cheaply and for free.
    response_lower = trajectory.final_response.lower()
    for phrase in case.expected_final_response.must_not_include:
        if phrase.lower() in response_lower:
            failures.append(f"final response contains a forbidden phrase: {phrase!r}")

    return GradeResult(
        case_id=case.id,
        passed_structural=not failures,
        structural_failures=failures,
        judged_checks_pending=[
            *[f"contract: {c}" for c in case.tool_trajectory_contract],
            *[f"forbidden: {f}" for f in case.forbidden],
            *[f"fail_if: {f}" for f in case.fail_if],
        ],
    )


def judge_with_llm(case: EvalCase, trajectory: Trajectory) -> None:
    """
    Intentionally unimplemented. This is where an LLM-as-judge pass would
    evaluate the natural-language contracts in `case.tool_trajectory_contract`,
    `case.forbidden`, and `case.fail_if` against the captured trajectory.

    Not built now because there's no real trajectory yet to judge — only
    hand-built demo ones (see evals/run.py). Wire this up once Phase 3/6
    produce real trajectories worth spending judge-model calls on.
    """
    raise NotImplementedError(
        "judge_with_llm is a documented extension point, not a stub to call yet — "
        "see the module docstring."
    )
