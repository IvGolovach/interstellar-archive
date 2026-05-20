"""Utility helpers for the mission baseline layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .constants import PARAMETER_CLAIMS_PATH


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_claims_map(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    claims_path = repo_root / PARAMETER_CLAIMS_PATH
    if not claims_path.exists():
        return {}
    payload = load_json(claims_path)
    claims = payload.get("claims", [])
    if not isinstance(claims, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            out[str(claim["parameter_id"])] = claim
    return out


def _round(value: float, digits: int = 12) -> float:
    return float(f"{value:.{digits}f}")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _get_path(data: Mapping[str, Any], dotted_path: str) -> float:
    cursor: Any = data
    for key in dotted_path.split("."):
        cursor = cursor[key]
    if isinstance(cursor, bool) or not isinstance(cursor, (int, float)):
        raise TypeError(f"path '{dotted_path}' is not numeric")
    return float(cursor)


def _set_path(data: Dict[str, Any], dotted_path: str, value: float) -> None:
    cursor: Any = data
    parts = dotted_path.split(".")
    for key in parts[:-1]:
        cursor = cursor[key]
    cursor[parts[-1]] = value
