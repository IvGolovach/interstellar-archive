"""Shim that exposes the shared script bootstrap helper inside scripts/ci."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = SCRIPTS_ROOT / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("scripts_shared_bootstrap", BOOTSTRAP_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load shared bootstrap helper: {BOOTSTRAP_PATH}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

bootstrap_repo_root = _module.bootstrap_repo_root
ensure_repo_on_path = _module.ensure_repo_on_path
resolve_repo_root = _module.resolve_repo_root

__all__ = [
    "bootstrap_repo_root",
    "ensure_repo_on_path",
    "resolve_repo_root",
]
