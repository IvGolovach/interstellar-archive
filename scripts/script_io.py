"""Shared JSON and text IO helpers for direct script entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


TextRenderer = Callable[[Any], str]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(
    payload: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> str:
    return json.dumps(payload, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)


def render_output(
    payload: Any,
    *,
    output_format: str,
    text_renderer: TextRenderer,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> str:
    if output_format == "json":
        return render_json(payload, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    return text_renderer(payload)


def write_text(path: Path, content: str, *, ensure_trailing_newline: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content
    if ensure_trailing_newline and not normalized.endswith("\n"):
        normalized += "\n"
    path.write_text(normalized, encoding="utf-8")


def write_json(
    path: Path,
    payload: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> None:
    write_text(
        path,
        render_json(
            payload,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
        ),
    )

