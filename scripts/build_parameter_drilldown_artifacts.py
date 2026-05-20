#!/usr/bin/env python3
"""Build deterministic tracked artifacts for parameter drilldown v1."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .parameter_drilldown_builder import (
        DEFAULT_EVIDENCE_INDEX,
        DEFAULT_EVIDENCE_SOURCES,
        DEFAULT_FAILURE_TAXONOMY,
        DEFAULT_MANIFEST,
        DEFAULT_MODULE_REGISTRY,
        DEFAULT_PARAMETER_CLAIMS,
        DEFAULT_PARAMETER_REGISTRY,
        DEFAULT_P_SUCCESS_DEFENSIBILITY,
        DEFAULT_RUNNER_PATH,
        DEFAULT_SENSITIVITY_RESULTS,
        DEFAULT_STATIC_GRAPH,
        DEFAULT_UNCERTAINTY_MODEL,
        build_artifacts,
    )
    from .script_io import render_json
except ImportError:
    from parameter_drilldown_builder import (
        DEFAULT_EVIDENCE_INDEX,
        DEFAULT_EVIDENCE_SOURCES,
        DEFAULT_FAILURE_TAXONOMY,
        DEFAULT_MANIFEST,
        DEFAULT_MODULE_REGISTRY,
        DEFAULT_PARAMETER_CLAIMS,
        DEFAULT_PARAMETER_REGISTRY,
        DEFAULT_P_SUCCESS_DEFENSIBILITY,
        DEFAULT_RUNNER_PATH,
        DEFAULT_SENSITIVITY_RESULTS,
        DEFAULT_STATIC_GRAPH,
        DEFAULT_UNCERTAINTY_MODEL,
        build_artifacts,
    )
    from script_io import render_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--parameter-registry", default=str(DEFAULT_PARAMETER_REGISTRY))
    parser.add_argument("--parameter-claims", default=str(DEFAULT_PARAMETER_CLAIMS))
    parser.add_argument("--evidence-sources", default=str(DEFAULT_EVIDENCE_SOURCES))
    parser.add_argument("--uncertainty-model", default=str(DEFAULT_UNCERTAINTY_MODEL))
    parser.add_argument("--module-registry", default=str(DEFAULT_MODULE_REGISTRY))
    parser.add_argument("--failure-taxonomy", default=str(DEFAULT_FAILURE_TAXONOMY))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER_PATH))
    parser.add_argument("--static-graph", default=str(DEFAULT_STATIC_GRAPH))
    parser.add_argument("--evidence-index", default=str(DEFAULT_EVIDENCE_INDEX))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--p-success-defensibility", default=str(DEFAULT_P_SUCCESS_DEFENSIBILITY))
    parser.add_argument("--sensitivity-results", default=str(DEFAULT_SENSITIVITY_RESULTS))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    result = build_artifacts(
        repo_root=repo_root,
        parameter_registry_path=Path(args.parameter_registry),
        parameter_claims_path=Path(args.parameter_claims),
        evidence_sources_path=Path(args.evidence_sources),
        uncertainty_model_path=Path(args.uncertainty_model),
        module_registry_path=Path(args.module_registry),
        failure_taxonomy_path=Path(args.failure_taxonomy),
        runner_path=Path(args.runner),
        static_graph_path=Path(args.static_graph),
        evidence_index_path=Path(args.evidence_index),
        manifest_path=Path(args.manifest),
        p_success_defensibility_path=Path(args.p_success_defensibility),
        sensitivity_results_path=Path(args.sensitivity_results),
    )
    if args.format == "json":
        print(render_json(result))
    else:
        status = "PASS" if not result["integrity_errors"] else "FAIL"
        print(f"{status}: parameter drilldown artifacts")
        print(f"- parameter_count: {result['parameter_count']}")
        print(f"- excluded_internal_parameter_count: {result['excluded_internal_parameter_count']}")
        print(f"- global_evidence_completeness_ratio: {result['global_evidence_completeness_ratio']:.6f}")
        print(f"- static_graph_sha256: {result['static_graph_sha256']}")
        print(f"- evidence_index_sha256: {result['evidence_index_sha256']}")
        print(f"- p_success_defensibility_sha256: {result['p_success_defensibility_sha256']}")
        print(f"- manifest_sha256: {result['manifest_sha256']}")
        if result["integrity_errors"]:
            print(f"- integrity_errors: {len(result['integrity_errors'])}")
            for error in result["integrity_errors"]:
                print(f"  - {error}")
    if result["integrity_errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
