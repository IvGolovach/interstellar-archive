"""Shim that exposes shared script IO helpers inside scripts/ci."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
IO_PATH = SCRIPTS_ROOT / "script_io.py"
_spec = importlib.util.spec_from_file_location("scripts_shared_io", IO_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load shared IO helper: {IO_PATH}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

load_json = _module.load_json
render_json = _module.render_json
render_output = _module.render_output
write_json = _module.write_json
write_text = _module.write_text

__all__ = [
    "load_json",
    "render_json",
    "render_output",
    "write_json",
    "write_text",
]

