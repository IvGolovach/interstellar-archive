#!/usr/bin/env python3
"""Fail fast when commands are not executed from repository root."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

try:
    from .script_io import render_output, write_text
except ImportError:
    from script_io import render_output, write_text

EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


def _git_toplevel(cwd: Path) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git rev-parse failed")
    return Path(proc.stdout.strip()).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--strict", action="store_true", default=True)
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def _render_text(payload: dict[str, str]) -> str:
    lines = [
        f"{payload['status']}: repo root guard",
        f"- cwd: {payload['cwd']}",
        f"- expected: {payload['expected']}",
        f"- git_toplevel: {payload['git_toplevel']}",
    ]
    if payload["status"] != "PASS":
        lines.append("- fix: run commands from repository root to avoid path/import ambiguity")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    cwd = Path.cwd().resolve()
    expected = Path(args.repo_root).resolve()

    try:
        toplevel = _git_toplevel(cwd)
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL

    ok = cwd == expected == toplevel
    payload = {
        "status": "PASS" if ok else "FAIL",
        "cwd": str(cwd),
        "expected": str(expected),
        "git_toplevel": str(toplevel),
    }
    rendered = render_output(payload, output_format=args.format, text_renderer=_render_text)
    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)

    if ok:
        return EXIT_PASS
    return EXIT_VIOLATION if args.strict else EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
