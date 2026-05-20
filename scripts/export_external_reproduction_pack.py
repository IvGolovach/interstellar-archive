#!/usr/bin/env python3
"""Export a reviewer-owned external reproduction pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission.external_reproduction import export_external_reproduction_pack, validate_exported_external_reproduction_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--no-zip", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    result = export_external_reproduction_pack(
        repo_root=repo_root,
        output_dir=output_dir,
        make_zip=not args.no_zip,
    )
    errors = validate_exported_external_reproduction_pack(result["pack_root"])
    payload = {
        "status": "PASS" if not errors else "FAIL",
        "pack_root": str(result["pack_root"]),
        "zip_path": str(result["zip_path"]) if result["zip_path"] else None,
        "pack_file_count": len(result["manifest"]["pack_files"]),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['status']}: external reproduction pack export")
        print(f"- pack_root: {payload['pack_root']}")
        print(f"- zip_path: {payload['zip_path']}")
        print(f"- pack_file_count: {payload['pack_file_count']}")
        for error in errors:
            print(f"- error: {error}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
