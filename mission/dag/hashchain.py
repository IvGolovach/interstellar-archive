"""Deterministic hashchain utilities for mission DAG artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(payload: str | bytes) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65_536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def append_entry(
    entries: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    node_id: str,
    module_id: str,
    artifact_path: str,
    artifact_hash: str,
) -> Dict[str, Any]:
    prev_hash = entries[-1]["chain_hash"] if entries else "0" * 64
    entry = {
        "index": len(entries),
        "mode": mode,
        "node_id": node_id,
        "module_id": module_id,
        "artifact_path": artifact_path,
        "artifact_hash": artifact_hash,
        "prev_hash": prev_hash,
    }
    chain_hash = sha256_hex(_canonical_json(entry))
    return {**entry, "chain_hash": chain_hash}


def verify_chain(entries: Iterable[Mapping[str, Any]]) -> Tuple[bool, str]:
    previous = "0" * 64
    for index, entry in enumerate(entries):
        if entry.get("index") != index:
            return False, f"index mismatch at position {index}"
        if entry.get("prev_hash") != previous:
            return False, f"prev_hash mismatch at position {index}"

        current = dict(entry)
        chain_hash = current.pop("chain_hash", None)
        if not isinstance(chain_hash, str):
            return False, f"missing chain_hash at position {index}"

        expected = sha256_hex(_canonical_json(current))
        if expected != chain_hash:
            return False, f"chain_hash mismatch at position {index}"

        previous = chain_hash

    return True, "ok"


def write_jsonl(path: Path, entries: Sequence[Mapping[str, Any]]) -> None:
    lines = [json.dumps(dict(entry), sort_keys=True) for entry in entries]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        out.append(json.loads(stripped))
    return out


def build_manifest(paths: Iterable[Path], root: Path) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    for path in sorted(paths):
        rel = str(path.relative_to(root))
        manifest[rel] = file_sha256(path)
    return manifest
