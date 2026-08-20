"""
Captures what actually happened during a (real or simulated) agent run,
so a Grader can check it against an EvalCase's contracts.

This is the shape any future agent implementation needs to produce during
an eval run. Right now nothing populates it from a real call — Phase 3+
wires the real agent to fill this in. Until then, tests/demos build a
Trajectory by hand to prove the grading logic itself is correct.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict
    restaurant_id: str | None = None  # what the call actually carried — the thing wrong_restaurant_scope.yaml exists to catch
    result: Any = None
    ok: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Trajectory:
    case_id: str
    interpreted_intent: str = ""
    interpreted_entities: dict = field(default_factory=dict)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    state_changes: list[str] = field(default_factory=list)
    final_response: str = ""

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        restaurant_id: str | None = None,
        result: Any = None,
        ok: bool = True,
    ) -> None:
        self.tool_calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                arguments=arguments,
                restaurant_id=restaurant_id,
                result=result,
                ok=ok,
            )
        )

    def tool_names_in_order(self) -> list[str]:
        return [c.tool_name for c in self.tool_calls]
