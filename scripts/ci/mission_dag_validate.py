#!/usr/bin/env python3
"""Validate mission DAG contracts, registries, and optional run artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text
import sys
from typing import Any, Dict, List, Mapping

REPO_ROOT = bootstrap_repo_root(__file__, levels=2)

from mission.dag import contracts
from mission.dag import hashchain as hashchain_lib


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_SCENARIO = Path("mission/dag/scenarios/mission_dag_baseline.v1.json")
DEFAULT_MODULE_REGISTRY = Path("mission/dag/registry/module_registry.v1.json")
DEFAULT_FAILURE_TAXONOMY = Path("mission/dag/registry/failure_taxonomy.v1.json")
SCHEMA_FILES = (
    Path("mission/dag/schema/module_io.schema.v1.json"),
    Path("mission/dag/schema/scenario_dag.schema.v1.json"),
    Path("mission/dag/schema/failure_taxonomy.schema.v1.json"),
)


def _validate_artifacts(
    *,
    repo_root: Path,
    artifacts_dir: Path,
    taxonomy: Mapping[str, Any],
) -> List[str]:
    errors: List[str] = []
    taxonomy_by_id = contracts.taxonomy_map(taxonomy)

    def _display(path: Path) -> str:
        try:
            return str(path.relative_to(repo_root))
        except ValueError:
            return str(path)

    if not artifacts_dir.exists():
        return [f"artifacts dir does not exist: {artifacts_dir}"]

    module_files = sorted((artifacts_dir / "modules").glob("**/*.json"))
    if not module_files:
        errors.append("artifacts/modules contains no module json files")
    for module_file in module_files:
        payload = load_json(module_file)
        file_errors = contracts.validate_module_output(payload, taxonomy_by_id)
        for error in file_errors:
            errors.append(f"{_display(module_file)}: {error}")

    hashchain_path = artifacts_dir / "hashchain.jsonl"
    if hashchain_path.exists():
        chain_entries = hashchain_lib.read_jsonl(hashchain_path)
        ok, reason = hashchain_lib.verify_chain(chain_entries)
        if not ok:
            errors.append(f"hashchain invalid: {reason}")

        for entry in chain_entries:
            rel = str(entry.get("artifact_path", ""))
            artifact_path = artifacts_dir / rel
            if not artifact_path.exists():
                errors.append(f"hashchain artifact missing: {rel}")
                continue
            actual = hashchain_lib.file_sha256(artifact_path)
            expected = str(entry.get("artifact_hash", ""))
            if actual != expected:
                errors.append(f"hashchain artifact hash mismatch: {rel}")
    else:
        errors.append("hashchain.jsonl missing in artifacts dir")

    manifest_path = artifacts_dir / "manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        files = manifest.get("files")
        if not isinstance(files, Mapping):
            errors.append("manifest.json files must be an object")
        else:
            manifest_hash = contracts.manifest_hash({str(k): str(v) for k, v in files.items()})
            if manifest_hash != manifest.get("manifest_hash"):
                errors.append("manifest_hash mismatch")
    else:
        errors.append("manifest.json missing in artifacts dir")

    return errors


def run_validation(
    *,
    repo_root: Path,
    scenario_path: Path,
    module_registry_path: Path,
    failure_taxonomy_path: Path,
    artifacts_dir: Path | None,
) -> Dict[str, Any]:
    errors: List[str] = []

    for schema_file in SCHEMA_FILES:
        if not (repo_root / schema_file).exists():
            errors.append(f"missing schema file: {schema_file}")
        else:
            try:
                load_json(repo_root / schema_file)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"invalid json in {schema_file}: {exc}")

    module_registry = load_json(repo_root / module_registry_path)
    failure_taxonomy = load_json(repo_root / failure_taxonomy_path)
    scenario = load_json(repo_root / scenario_path)

    errors.extend(contracts.validate_module_registry(module_registry, repo_root=repo_root))
    errors.extend(contracts.validate_failure_taxonomy(failure_taxonomy))
    errors.extend(contracts.validate_scenario_dag(scenario, module_registry))

    if artifacts_dir is not None:
        errors.extend(
            _validate_artifacts(
                repo_root=repo_root,
                artifacts_dir=artifacts_dir,
                taxonomy=failure_taxonomy,
            )
        )

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "scenario": str(scenario_path),
        "module_registry": str(module_registry_path),
        "failure_taxonomy": str(failure_taxonomy_path),
        "artifacts_dir": str(artifacts_dir) if artifacts_dir else None,
    }


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: mission DAG validation",
        f"- scenario: {result['scenario']}",
        f"- module_registry: {result['module_registry']}",
        f"- failure_taxonomy: {result['failure_taxonomy']}",
    ]
    if result.get("artifacts_dir"):
        lines.append(f"- artifacts_dir: {result['artifacts_dir']}")

    errors = result.get("errors", [])
    if errors:
        lines.append("- errors:")
        for error in errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    parser.add_argument("--module-registry", default=str(DEFAULT_MODULE_REGISTRY))
    parser.add_argument("--failure-taxonomy", default=str(DEFAULT_FAILURE_TAXONOMY))
    parser.add_argument("--artifacts-dir")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        artifacts_dir = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
        result = run_validation(
            repo_root=repo_root,
            scenario_path=Path(args.scenario),
            module_registry_path=Path(args.module_registry),
            failure_taxonomy_path=Path(args.failure_taxonomy),
            artifacts_dir=artifacts_dir,
        )

        rendered = render_output(result, output_format=args.format, text_renderer=_render_text)
        print(rendered)

        if args.output:
            write_text(Path(args.output), rendered)

        if result["status"] == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            write_text(Path(args.output), message)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
