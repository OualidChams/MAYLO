"""
Runnable proof that the eval harness actually works, using hand-built
Trajectory objects standing in for a real agent (which doesn't exist yet).

Usage:
    python -m evals.run
"""
from __future__ import annotations

from evals.grader import grade_structural
from evals.loader import load_eval_case_by_id, load_eval_cases
from evals.trajectory import Trajectory


def print_dataset_summary() -> None:
    cases = load_eval_cases()
    by_category: dict[str, int] = {}
    for case in cases:
        top_level = case.category.split("/")[0]
        by_category[top_level] = by_category.get(top_level, 0) + 1

    print(f"Loaded {len(cases)} eval cases from eval_cases/")
    for category, count in sorted(by_category.items()):
        print(f"  {category}: {count}")
    print()


def smoke_test_scope_violation_is_caught() -> None:
    """
    Builds a deliberately WRONG trajectory for wrong_restaurant_scope.yaml
    (a tool call carrying restaurant_id='456' instead of the call's actual
    'REST_A') and confirms the structural grader catches it. This is the
    single most important regression test in the project, per the eval
    case's own description.
    """
    case = load_eval_case_by_id("authorization_wrong_restaurant_scope")

    bad_trajectory = Trajectory(case_id=case.id, final_response="Here's your order info.")
    bad_trajectory.record_tool_call(
        tool_name="get_order",
        arguments={"order_id": "abc"},
        restaurant_id="456",  # BUG: should be REST_A, taken from the call session
    )

    result = grade_structural(case, bad_trajectory)
    print(f"Smoke test 1 (deliberately bad trajectory): {result.summary}")
    assert not result.passed_structural, "grader failed to catch a scope violation!"
    for failure in result.structural_failures:
        print(f"  caught: {failure}")
    print()


def smoke_test_correct_trajectory_passes_structural() -> None:
    """Same case, but with a correctly-scoped trajectory — confirms the
    grader doesn't produce false positives on the happy path."""
    case = load_eval_case_by_id("authorization_wrong_restaurant_scope")

    good_trajectory = Trajectory(
        case_id=case.id,
        final_response="I can only help with orders for this restaurant.",
    )
    good_trajectory.record_tool_call(
        tool_name="get_order",
        arguments={"order_id": "abc"},
        restaurant_id="REST_A",  # correct — taken from the call session
    )

    result = grade_structural(case, good_trajectory)
    print(f"Smoke test 2 (correctly-scoped trajectory): {result.summary}")
    assert result.passed_structural, "grader produced a false positive!"
    print(f"  {len(result.judged_checks_pending)} contracts still need judged review "
          f"(expected — see evals/grader.py docstring)")
    print()


if __name__ == "__main__":
    print_dataset_summary()
    smoke_test_scope_violation_is_caught()
    smoke_test_correct_trajectory_passes_structural()
    print("All smoke tests passed. Harness is ready for Phase 3/6 to plug a real agent into.")
