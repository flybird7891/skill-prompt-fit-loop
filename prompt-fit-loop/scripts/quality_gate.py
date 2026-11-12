#!/usr/bin/env python3
"""Deterministic satisfaction gate for prompt-fit-loop."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


THRESHOLD_MIN = 0.50
THRESHOLD_MAX = 0.95
ROUNDS_MIN = 1
ROUNDS_MAX = 5
PRIORITY_WEIGHTS = {"P0": 3.0, "P1": 2.0, "P2": 1.0}
STATUS_SCORES = {
    "met": 1.0,
    "partial": 0.5,
    "unmet": 0.0,
    "unverifiable": 0.0,
}


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def validate_config(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")

    threshold = _finite_number(data.get("threshold"), "threshold")
    if not THRESHOLD_MIN <= threshold <= THRESHOLD_MAX:
        raise ValueError(
            f"threshold must be between {THRESHOLD_MIN:.2f} and "
            f"{THRESHOLD_MAX:.2f}"
        )

    max_rounds = _integer(data.get("max_rounds"), "max_rounds")
    if not ROUNDS_MIN <= max_rounds <= ROUNDS_MAX:
        raise ValueError(
            f"max_rounds must be between {ROUNDS_MIN} and {ROUNDS_MAX}"
        )

    current_round = _integer(data.get("current_round"), "current_round")
    if not ROUNDS_MIN <= current_round <= max_rounds:
        raise ValueError("current_round must be between 1 and max_rounds")

    raw_requirements = data.get("requirements")
    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise ValueError("requirements must be a non-empty list")

    requirements: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, raw in enumerate(raw_requirements, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"requirements[{index}] must be an object")

        requirement_id = raw.get("id")
        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise ValueError(f"requirements[{index}].id must be a non-empty string")
        requirement_id = requirement_id.strip()
        if requirement_id in seen_ids:
            raise ValueError(f"duplicate requirement id: {requirement_id}")
        seen_ids.add(requirement_id)

        priority = raw.get("priority")
        if not isinstance(priority, str):
            raise ValueError(f"{requirement_id}.priority must be P0, P1, or P2")
        priority = priority.upper()
        if priority not in PRIORITY_WEIGHTS:
            raise ValueError(f"{requirement_id}.priority must be P0, P1, or P2")

        status = raw.get("status")
        if not isinstance(status, str):
            raise ValueError(f"{requirement_id}.status is required")
        status = status.lower()
        if status not in STATUS_SCORES:
            allowed = ", ".join(STATUS_SCORES)
            raise ValueError(f"{requirement_id}.status must be one of: {allowed}")

        evidence = raw.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(f"{requirement_id}.evidence must be non-empty")

        if "weight" in raw:
            weight = _finite_number(raw["weight"], f"{requirement_id}.weight")
            if weight <= 0:
                raise ValueError(f"{requirement_id}.weight must be greater than zero")
            weight_source = "explicit"
        else:
            weight = PRIORITY_WEIGHTS[priority]
            weight_source = "priority_default"

        requirements.append(
            {
                "id": requirement_id,
                "priority": priority,
                "status": status,
                "evidence": evidence.strip(),
                "weight": weight,
                "weight_source": weight_source,
            }
        )

    return {
        "threshold": threshold,
        "max_rounds": max_rounds,
        "current_round": current_round,
        "requirements": requirements,
    }


def evaluate(data: Any) -> dict[str, Any]:
    config = validate_config(data)
    total_weight = 0.0
    weighted_score = 0.0
    critical_failures: list[str] = []
    results: list[dict[str, Any]] = []

    for requirement in config["requirements"]:
        item_score = STATUS_SCORES[requirement["status"]]
        contribution = requirement["weight"] * item_score
        total_weight += requirement["weight"]
        weighted_score += contribution

        if requirement["priority"] == "P0" and requirement["status"] != "met":
            critical_failures.append(requirement["id"])

        results.append(
            {
                "id": requirement["id"],
                "priority": requirement["priority"],
                "status": requirement["status"],
                "score": item_score,
                "weight": requirement["weight"],
                "weighted_contribution": round(contribution, 6),
                "weight_source": requirement["weight_source"],
                "evidence": requirement["evidence"],
            }
        )

    satisfaction = round(weighted_score / total_weight, 6)
    threshold = config["threshold"]
    current_round = config["current_round"]
    max_rounds = config["max_rounds"]
    score_passes = satisfaction >= threshold
    p0_passes = not critical_failures

    if score_passes and p0_passes:
        decision = "pass"
        reason = "Satisfaction threshold reached and all P0 requirements are met."
    elif current_round >= max_rounds:
        decision = "stop_failed"
        if critical_failures:
            reason = "Maximum rounds reached; one or more P0 requirements are unmet."
        else:
            reason = "Maximum rounds reached; satisfaction remains below threshold."
    else:
        decision = "revise"
        if critical_failures:
            reason = "Revision required because one or more P0 requirements are unmet."
        else:
            reason = "Revision required because satisfaction is below threshold."

    return {
        "satisfaction_score": satisfaction,
        "threshold": threshold,
        "score_passes": score_passes,
        "p0_passes": p0_passes,
        "critical_failures": critical_failures,
        "current_round": current_round,
        "max_rounds": max_rounds,
        "rounds_remaining": max(0, max_rounds - current_round),
        "decision": decision,
        "reason": reason,
        "requirements": results,
    }


def _read_input(path: str) -> Any:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("input JSON is empty")
    return json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a prompt-fit-loop scoring state and calculate the gate."
    )
    parser.add_argument(
        "--input",
        default="-",
        help="Path to a JSON state file, or '-' to read standard input.",
    )
    args = parser.parse_args()

    try:
        result = evaluate(_read_input(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"quality_gate: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
