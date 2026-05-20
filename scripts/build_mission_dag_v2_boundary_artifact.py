#!/usr/bin/env python3
"""Build Mission DAG v2 module-boundary artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root
try:
    from .script_io import load_json, render_json, write_json
except ImportError:
    from script_io import load_json, render_json, write_json

REPO_ROOT = bootstrap_repo_root(__file__, levels=1)

from mission.dag import boundary_v2


DEFAULT_MODULE_REGISTRY = Path("mission/dag/registry/module_registry.v1.json")
DEFAULT_SCENARIO = Path("mission/dag/scenarios/mission_dag_baseline.v1.json")
DEFAULT_FAILURE_TAXONOMY = Path("mission/dag/registry/failure_taxonomy.v1.json")
DEFAULT_MODULE_SCHEMA = Path("mission/dag/schema/module_io.schema.v1.json")
DEFAULT_SCENARIO_SCHEMA = Path("mission/dag/schema/scenario_dag.schema.v1.json")
DEFAULT_TAXONOMY_SCHEMA = Path("mission/dag/schema/failure_taxonomy.schema.v1.json")
DEFAULT_RUNNER = Path("mission/dag/runner_v1.py")
DEFAULT_CONTRACTS = Path("mission/dag/contracts.py")
DEFAULT_HASHCHAIN = Path("mission/dag/hashchain.py")
DEFAULT_VALIDATOR = Path("scripts/ci/mission_dag_validate.py")
DEFAULT_OUTPUT = Path("artifacts/mission_dag_v2_boundary.v1.json")


def build_payload(
    *,
    repo_root: Path,
    module_registry_path: Path = DEFAULT_MODULE_REGISTRY,
    scenario_path: Path = DEFAULT_SCENARIO,
    failure_taxonomy_path: Path = DEFAULT_FAILURE_TAXONOMY,
    module_schema_path: Path = DEFAULT_MODULE_SCHEMA,
    scenario_schema_path: Path = DEFAULT_SCENARIO_SCHEMA,
    taxonomy_schema_path: Path = DEFAULT_TAXONOMY_SCHEMA,
    runner_path: Path = DEFAULT_RUNNER,
    contracts_path: Path = DEFAULT_CONTRACTS,
    hashchain_path: Path = DEFAULT_HASHCHAIN,
    validator_path: Path = DEFAULT_VALIDATOR,
) -> Dict[str, Any]:
    source_paths = [
        str(module_registry_path),
        str(scenario_path),
        str(failure_taxonomy_path),
        str(module_schema_path),
        str(scenario_schema_path),
        str(taxonomy_schema_path),
        str(runner_path),
        str(contracts_path),
        str(hashchain_path),
        str(validator_path),
    ]
    for path in source_paths:
        if not (repo_root / path).exists():
            raise FileNotFoundError(path)

    module_registry = load_json(repo_root / module_registry_path)
    scenario = load_json(repo_root / scenario_path)
    failure_taxonomy = load_json(repo_root / failure_taxonomy_path)
    module_boundaries = boundary_v2.build_module_boundaries(
        module_registry=module_registry,
        scenario=scenario,
        failure_taxonomy=failure_taxonomy,
    )
    payload: Dict[str, Any] = {
        "schema_version": boundary_v2.SCHEMA_VERSION,
        "generator": boundary_v2.GENERATOR,
        "public_scope": boundary_v2.PUBLIC_SCOPE,
        "non_certification_notice": True,
        "source_artifacts": boundary_v2.source_artifacts(repo_root, source_paths),
        "module_count": len(module_boundaries),
        "registry_version": module_registry.get("registry_version"),
        "scenario_ref": str(scenario_path),
        "scenario_id": scenario.get("scenario_id"),
        "failure_taxonomy_ref": str(failure_taxonomy_path),
        "module_boundaries": module_boundaries,
        "rollup": boundary_v2.rollup(module_boundaries),
        "blocked_claims": list(boundary_v2.BLOCKED_CLAIMS),
        "interpretation_limits": list(boundary_v2.INTERPRETATION_LIMITS),
        "external_evidence_gaps": sorted(
            {
                gap
                for row in module_boundaries
                for gap in row.get("open_external_evidence_gaps", [])
                if isinstance(gap, str)
            }
        ),
    }
    payload["determinism_signature"] = boundary_v2.sha256_payload(
        {
            "module_count": payload["module_count"],
            "module_boundaries": payload["module_boundaries"],
            "rollup": payload["rollup"],
            "blocked_claims": payload["blocked_claims"],
            "external_evidence_gaps": payload["external_evidence_gaps"],
        }
    )
    return payload


def build_and_write(*, repo_root: Path, output_path: Path) -> Dict[str, Any]:
    payload = build_payload(repo_root=repo_root)
    write_json(repo_root / output_path, payload)
    return {
        "status": "PASS",
        "output": str(output_path),
        "module_count": payload["module_count"],
        "taxonomy_mapped_count": payload["rollup"]["failure_taxonomy_mapping_module_count"],
        "sha256": boundary_v2.sha256_payload(payload),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_and_write(repo_root=Path(args.repo_root).resolve(), output_path=Path(args.output))
        if args.format == "json":
            print(render_json(result))
        else:
            print("PASS: mission DAG v2 boundary artifact")
            print(f"- output: {result['output']}")
            print(f"- module_count: {result['module_count']}")
            print(f"- taxonomy_mapped_count: {result['taxonomy_mapped_count']}")
            print(f"- sha256: {result['sha256']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
