"""Deterministic git helpers for governance checks."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set


class GitCommandError(RuntimeError):
    """Raised when a git command fails."""


class FileDecodeError(ValueError):
    """Raised when file content cannot be decoded as UTF-8."""


def _stable_env() -> Dict[str, str]:
    env = dict()
    env.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
        }
    )
    return env


def run_git(repo_root: Path, args: Sequence[str], allow_failure: bool = False) -> bytes:
    """Run git in deterministic locale and return stdout bytes."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env={**os.environ, **_stable_env()},
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        raise GitCommandError(
            f"git {' '.join(args)} failed with code {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


@dataclass(frozen=True)
class ChangedFile:
    status: str
    raw_status: str
    path: str
    old_path: Optional[str] = None
    new_path: Optional[str] = None

    def touched_paths(self) -> Set[str]:
        paths: Set[str] = set()
        if self.path:
            paths.add(self.path)
        if self.old_path:
            paths.add(self.old_path)
        if self.new_path:
            paths.add(self.new_path)
        return paths


def _decode_path(raw: bytes) -> str:
    return raw.decode("utf-8", errors="surrogateescape")


def parse_name_status_z(output: bytes) -> List[ChangedFile]:
    """Parse `git diff --name-status -z` output."""
    if not output:
        return []
    tokens = output.split(b"\x00")
    if tokens and tokens[-1] == b"":
        tokens = tokens[:-1]
    changed: List[ChangedFile] = []
    idx = 0
    while idx < len(tokens):
        raw_status = tokens[idx].decode("ascii")
        idx += 1
        status = raw_status[:1]
        if status in {"R", "C"}:
            if idx + 1 >= len(tokens):
                raise GitCommandError("malformed --name-status -z output for rename/copy entry")
            old_path = _decode_path(tokens[idx])
            new_path = _decode_path(tokens[idx + 1])
            idx += 2
            changed.append(
                ChangedFile(
                    status=status,
                    raw_status=raw_status,
                    path=new_path,
                    old_path=old_path,
                    new_path=new_path,
                )
            )
            continue

        if idx >= len(tokens):
            raise GitCommandError("malformed --name-status -z output for non-rename entry")
        path = _decode_path(tokens[idx])
        idx += 1
        changed.append(ChangedFile(status=status, raw_status=raw_status, path=path))
    return changed


def changed_files(repo_root: Path, base: str, head: str) -> List[ChangedFile]:
    output = run_git(repo_root, ["diff", "--name-status", "-z", base, head])
    return parse_name_status_z(output)


def commit_range(repo_root: Path, base: str, head: str) -> List[str]:
    output = run_git(repo_root, ["rev-list", "--reverse", f"{base}..{head}"])
    text = output.decode("ascii", errors="strict").strip()
    return [line for line in text.splitlines() if line]


def is_file_changed(changed: Sequence[ChangedFile], path: str) -> bool:
    for item in changed:
        if path in item.touched_paths():
            return True
    return False


def file_contents_at(repo_root: Path, ref: str, path: str) -> str:
    output = file_bytes_at(repo_root, ref, path)
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FileDecodeError(f"file at {ref}:{path} is not valid UTF-8") from exc


def file_bytes_at(repo_root: Path, ref: str, path: str) -> bytes:
    return run_git(repo_root, ["show", f"{ref}:{path}"])


def file_exists_at(repo_root: Path, ref: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        cwd=repo_root,
        env={**os.environ, **_stable_env()},
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def diff_deleted_lines(repo_root: Path, base: str, head: str, path: str) -> List[str]:
    output = run_git(repo_root, ["diff", "--unified=0", base, head, "--", path])
    lines = output.decode("utf-8", errors="replace").splitlines()
    deleted: List[str] = []
    for line in lines:
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            deleted.append(line)
    return deleted
