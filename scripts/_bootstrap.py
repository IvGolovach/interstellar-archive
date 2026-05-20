"""Shared bootstrap helpers for direct script entrypoints."""

from __future__ import annotations

import sys
from pathlib import Path


def resolve_repo_root(script_file: str | Path, *, levels: int) -> Path:
    return Path(script_file).resolve().parents[levels]


def ensure_repo_on_path(repo_root: Path) -> Path:
    resolved = repo_root.resolve()
    repo_root_str = str(resolved)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return resolved


def bootstrap_repo_root(
    script_file: str | Path,
    *,
    levels: int,
    add_to_sys_path: bool = True,
) -> Path:
    repo_root = resolve_repo_root(script_file, levels=levels)
    if add_to_sys_path:
        return ensure_repo_on_path(repo_root)
    return repo_root

