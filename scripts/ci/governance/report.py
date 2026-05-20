"""Reporting utilities for governance checks."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from scripts.ci.governance.rules import GovernanceResult, Violation


def _violation_to_dict(violation: Violation) -> Dict[str, Any]:
    return {
        "rule_id": violation.rule_id,
        "severity": violation.severity,
        "evidence": violation.evidence,
        "fix": violation.fix,
    }


def result_to_json_dict(result: GovernanceResult) -> Dict[str, Any]:
    return {
        "status": result.status,
        "base": result.base,
        "head": result.head,
        "violations": [_violation_to_dict(item) for item in result.violations],
        "notes": list(result.notes),
    }


def render_json(result: GovernanceResult) -> str:
    return json.dumps(result_to_json_dict(result), indent=2, sort_keys=False)


def _format_evidence(evidence: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for key, value in evidence.items():
        lines.append(f"  {key}: {value}")
    return lines


def render_text(result: GovernanceResult) -> str:
    if result.status == "PASS":
        lines = [f"PASS: governance checks passed", f"- base: {result.base}", f"- head: {result.head}"]
        for note in result.notes:
            lines.append(f"- note: {note}")
        return "\n".join(lines)

    lines = [
        f"FAIL: governance violation ({len(result.violations)} rules)",
        f"- base: {result.base}",
        f"- head: {result.head}",
    ]
    for violation in result.violations:
        lines.append(f"- RULE: {violation.rule_id}")
        lines.extend(_format_evidence(violation.evidence))
        lines.append(f"  Fix: {violation.fix}")
    return "\n".join(lines)

