"""Loaders and utility helpers for evidence registries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Set


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "evidence"
REFS_BIB_PATH = REPO_ROOT / "refs" / "bibliography.bib"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_assumptions() -> Dict[str, Dict[str, Any]]:
    data = load_json(EVIDENCE_DIR / "assumptions.json")
    return {item["id"]: item for item in data["assumptions"]}


def load_sources() -> Dict[str, Dict[str, Any]]:
    data = load_json(EVIDENCE_DIR / "sources.json")
    return {item["id"]: item for item in data["sources"]}


def load_claims() -> Dict[str, Any]:
    return load_json(EVIDENCE_DIR / "claims.json")


def parse_bibliography_keys(bib_text: str) -> Set[str]:
    return set(re.findall(r"@\w+\{([^,]+),", bib_text))


def value_at_path(data: Dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def unique_ids(items: Iterable[Dict[str, Any]], key: str = "id") -> Set[str]:
    return {item[key] for item in items}

