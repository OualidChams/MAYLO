"""
Data model for eval cases loaded from eval_cases/**/*.yaml.

Mirrors the schema documented in eval_cases/README.md exactly. Kept
separate from app/ on purpose — this is dev-time tooling, not part of the
runtime call-handling path. It has no reason to import app.telephony or
app.db; it only needs to know the YAML shape and how to compare it
against a captured Trajectory.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpectedInterpretation:
    intent: str
    entities: dict = field(default_factory=dict)


@dataclass
class ExpectedFinalResponse:
    must_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)


@dataclass
class EvalCase:
    id: str
    category: str
    primary_failure_class: str
    description: str
    input_transcript: str
    input_context: dict
    expected_interpretation: ExpectedInterpretation
    tool_trajectory_contract: list[str]
    forbidden: list[str]
    expected_state_changes: list[str]
    expected_final_response: ExpectedFinalResponse
    fail_if: list[str]
    source_path: str

    @classmethod
    def from_yaml_dict(cls, data: dict, source_path: str) -> "EvalCase":
        interp = data.get("expected_interpretation") or {}
        resp = data.get("expected_final_response") or {}
        inp = data.get("input") or {}
        return cls(
            id=data["id"],
            category=data["category"],
            primary_failure_class=data.get("primary_failure_class", ""),
            description=(data.get("description") or "").strip(),
            input_transcript=inp.get("transcript", ""),
            input_context=inp.get("context") or {},
            expected_interpretation=ExpectedInterpretation(
                intent=interp.get("intent", ""),
                entities=interp.get("entities") or {},
            ),
            tool_trajectory_contract=data.get("tool_trajectory_contract") or [],
            forbidden=data.get("forbidden") or [],
            expected_state_changes=data.get("expected_state_changes") or [],
            expected_final_response=ExpectedFinalResponse(
                must_include=resp.get("must_include") or [],
                must_not_include=resp.get("must_not_include") or [],
            ),
            fail_if=data.get("fail_if") or [],
            source_path=source_path,
        )
