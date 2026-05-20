#!/usr/bin/env python3
"""Run deterministic golden evidence scenario and validate artifact integrity."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRATCH_ARTIFACTS_DIR = REPO_ROOT / ".tmp" / "golden-run-work"
PACK_DIR = REPO_ROOT / "artifacts" / "evidence-pack-v1"
REQUIRED_JSON = [
    PACK_DIR / "metadata.json",
    PACK_DIR / "input_parameters.json",
    PACK_DIR / "output_metrics.json",
]
REQUIRED_METADATA_FIELDS = [
    "commit_sha",
    "timestamp_utc",
    "python_version",
    "platform",
    "artifact_schema_version",
]


class GoldenRunError(RuntimeError):
    """Raised for invalid golden run state."""


def _git_head_sha() -> str:
    return (
        subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True)
        .strip()
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_builder(*, artifacts_dir: Path) -> None:
    subprocess.run(
        [
            "python3",
            "scripts/build_evidence_artifacts.py",
            "--repo-root",
            str(REPO_ROOT),
            "--artifacts-dir",
            str(artifacts_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def _read_json(path: Path) -> Dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GoldenRunError(f"missing required artifact file: {path.relative_to(REPO_ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise GoldenRunError(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}") from exc


def _load_checksums(pack_dir: Path) -> List[str]:
    checksums_path = pack_dir / "checksums.sha256"
    if not checksums_path.exists():
        raise GoldenRunError("missing checksums file: artifacts/evidence-pack-v1/checksums.sha256")

    lines = checksums_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        raise GoldenRunError("checksums.sha256 is empty")

    for line in lines:
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise GoldenRunError(f"invalid checksums line: {line}")
        expected, rel_path = parts
        if len(expected) != 64:
            raise GoldenRunError(f"invalid checksum digest: {expected}")
        target_path = REPO_ROOT / rel_path
        if not target_path.exists():
            raise GoldenRunError(f"checksummed path missing: {rel_path}")
        actual = _sha256(target_path)
        if actual != expected:
            raise GoldenRunError(f"checksum mismatch for {rel_path}: expected {expected}, actual {actual}")

    return lines


def validate_artifact_pack(pack_dir: Path) -> Dict[str, object]:
    required_json = [
        pack_dir / "metadata.json",
        pack_dir / "input_parameters.json",
        pack_dir / "output_metrics.json",
    ]
    parsed_json = {path.name: _read_json(path) for path in required_json}

    metadata = parsed_json["metadata.json"]
    missing = [field for field in REQUIRED_METADATA_FIELDS if field not in metadata]
    if missing:
        raise GoldenRunError(f"metadata.json missing required fields: {', '.join(missing)}")

    head_sha = _git_head_sha()
    if metadata["commit_sha"] != head_sha:
        raise GoldenRunError(
            f"metadata commit_sha mismatch: metadata={metadata['commit_sha']} git={head_sha}"
        )

    checksums_lines = _load_checksums(pack_dir)
    return {
        "head_sha": head_sha,
        "checksums_lines": checksums_lines,
        "output_metrics": parsed_json["output_metrics.json"],
        "pack_dir": str(pack_dir.relative_to(REPO_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-tracked-artifacts",
        action="store_true",
        help="Build into tracked artifacts/ (default builds in scratch dir and does not mutate tracked files).",
    )
    parser.add_argument(
        "--verify-deterministic",
        action="store_true",
        help="Run the golden scenario twice and fail if checksums differ",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    pack_dir: Path
    build_artifacts_dir: Path
    cleanup_scratch = False
    if args.refresh_tracked_artifacts:
        build_artifacts_dir = REPO_ROOT / "artifacts"
        pack_dir = PACK_DIR
    else:
        build_artifacts_dir = SCRATCH_ARTIFACTS_DIR
        pack_dir = build_artifacts_dir / "evidence-pack-v1"
        if build_artifacts_dir.exists():
            shutil.rmtree(build_artifacts_dir)
        build_artifacts_dir.mkdir(parents=True, exist_ok=True)
        cleanup_scratch = True

    try:
        run_builder(artifacts_dir=build_artifacts_dir)
        first = validate_artifact_pack(pack_dir)

        if args.verify_deterministic:
            first_checksums = "\n".join(first["checksums_lines"]) + "\n"
            run_builder(artifacts_dir=build_artifacts_dir)
            second = validate_artifact_pack(pack_dir)
            second_checksums = "\n".join(second["checksums_lines"]) + "\n"
            if first_checksums != second_checksums:
                raise GoldenRunError("golden run is non-deterministic: checksums differ between runs")

        metrics = first["output_metrics"]
        print("Golden run PASS")
        print(f"- commit_sha: {first['head_sha']}")
        print(f"- checks_total: {metrics['checks_total']}")
        print(f"- checks_passed: {metrics['checks_passed']}")
        print(f"- checksums_file: {first['pack_dir']}/checksums.sha256")
        return 0
    except (subprocess.CalledProcessError, GoldenRunError) as exc:
        print(f"Golden run FAIL: {exc}")
        return 1
    finally:
        if cleanup_scratch and SCRATCH_ARTIFACTS_DIR.exists():
            shutil.rmtree(SCRATCH_ARTIFACTS_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
