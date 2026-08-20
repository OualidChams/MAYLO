"""
Loads every eval_cases/**/*.yaml into EvalCase objects.
"""
from __future__ import annotations

import glob
import os

import yaml

from evals.models import EvalCase

DEFAULT_EVAL_CASES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "eval_cases")
)


def load_eval_cases(directory: str = DEFAULT_EVAL_CASES_DIR) -> list[EvalCase]:
    cases: list[EvalCase] = []
    pattern = os.path.join(directory, "**", "*.yaml")
    for path in sorted(glob.glob(pattern, recursive=True)):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        cases.append(EvalCase.from_yaml_dict(data, source_path=path))
    return cases


def load_eval_case_by_id(case_id: str, directory: str = DEFAULT_EVAL_CASES_DIR) -> EvalCase:
    for case in load_eval_cases(directory):
        if case.id == case_id:
            return case
    raise KeyError(f"No eval case with id={case_id!r} found under {directory}")
