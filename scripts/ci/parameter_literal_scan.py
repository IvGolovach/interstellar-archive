#!/usr/bin/env python3
"""Scan tracked mission/physics literals and enforce parameter-registry coverage."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set, Tuple

try:
    from .script_io import load_json, render_output, write_text
except ImportError:
    from script_io import load_json, render_output, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3


DEFAULT_REGISTRY = Path("parameters/registry/parameter_registry.v1.json")
DEFAULT_SCOPE_MANIFEST = Path("parameters/registry/parameter_literal_scope.v1.json")
SCOPE_MANIFEST_VERSION = "parameter_literal_scope.v1"


@dataclass(frozen=True)
class NumericRef:
    ref: str
    value: float
    scope: str


@dataclass(frozen=True)
class ScopeManifest:
    python_scope: Tuple[str, ...]
    json_scope: Tuple[str, ...]
    python_watched_roots: Tuple[str, ...]
    json_watched_roots: Tuple[str, ...]
    python_exclusions: Dict[str, str]
    json_exclusions: Dict[str, str]


class _ScopedNumericVisitor(ast.NodeVisitor):
    """Collect registry-tracked numeric literals using stable scope refs."""

    def __init__(self, rel_path: str, *, allowed_functions: Set[str] | None = None) -> None:
        self._rel_path = rel_path
        self._allowed_functions = allowed_functions
        self._function_stack: List[str] = []
        self._scope_counters: Dict[str, int] = {}
        self.items: List[NumericRef] = []

    def _append(self, scope_name: str, value: float) -> None:
        index = self._scope_counters.get(scope_name, 0)
        self._scope_counters[scope_name] = index + 1
        self.items.append(
            NumericRef(
                ref=f"{self._rel_path}::{scope_name}::literal[{index}]",
                value=float(value),
                scope="python",
            )
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        if not self._function_stack and self._rel_path == "mission/baseline/constants.py":
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            for target_name in target_names:
                if target_name in {"G", "C"}:
                    if (
                        isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, (int, float))
                        and not isinstance(node.value.value, bool)
                    ):
                        self.items.append(
                            NumericRef(
                                ref=f"{self._rel_path}::<module>::{target_name}",
                                value=float(node.value.value),
                                scope="python",
                            )
                        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
            return
        if not self._function_stack:
            if self._rel_path in {
                "scripts/benchmark_compare.py",
                "scripts/benchmark_drift_guard.py",
            }:
                self._append("<module>", float(node.value))
            return
        function_name = self._function_stack[-1]
        if self._allowed_functions is None or function_name in self._allowed_functions:
            self._append(function_name, float(node.value))


PYTHON_REF_SCOPES: Dict[str, Set[str] | None] = {
    "mission/baseline/constants.py": set(),
    "mission/baseline/model.py": {
        "schwarzschild_radius_m",
        "is_bh_environment_acceptable",
        "_compute_core_probabilities",
    },
    "scripts/benchmark_compare.py": None,
    "scripts/benchmark_drift_guard.py": None,
}


def _normalize_rel_path(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must contain non-empty relative paths")
    rel = raw.strip().replace("\\", "/")
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} contains unsafe path: {raw!r}")
    return rel


def _read_path_list(payload: Mapping[str, Any], key: str) -> Tuple[str, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        raise ValueError(f"scope manifest field '{key}' must be an array")
    paths = tuple(_normalize_rel_path(item, key) for item in raw)
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    if duplicates:
        raise ValueError(f"scope manifest field '{key}' contains duplicate paths: {duplicates}")
    return paths


def _read_exclusions(payload: Mapping[str, Any], key: str) -> Dict[str, str]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        raise ValueError(f"scope manifest field '{key}' must be an array")

    out: Dict[str, str] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{key}[{index}] must be an object")
        path = _normalize_rel_path(item.get("path"), f"{key}[{index}].path")
        rationale = item.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"{key}[{index}].rationale must be a non-empty string")
        if path in out:
            raise ValueError(f"{key} contains duplicate path: {path}")
        out[path] = rationale.strip()
    return out


def _ensure_disjoint(audit_paths: Sequence[str], exclusions: Mapping[str, str], field: str) -> None:
    overlap = sorted(set(audit_paths) & set(exclusions))
    if overlap:
        raise ValueError(f"scope manifest {field} paths cannot be both audited and excluded: {overlap}")


def load_scope_manifest(repo_root: Path, manifest_path: Path = DEFAULT_SCOPE_MANIFEST) -> ScopeManifest:
    payload = load_json(repo_root / manifest_path)
    if not isinstance(payload, dict):
        raise ValueError("scope manifest must be a JSON object")
    if payload.get("version") != SCOPE_MANIFEST_VERSION:
        raise ValueError(f"scope manifest version must be {SCOPE_MANIFEST_VERSION!r}")

    audit = payload.get("audit")
    watched_roots = payload.get("watched_roots")
    exclusions = payload.get("exclusions")
    if not isinstance(audit, dict):
        raise ValueError("scope manifest field 'audit' must be an object")
    if not isinstance(watched_roots, dict):
        raise ValueError("scope manifest field 'watched_roots' must be an object")
    if not isinstance(exclusions, dict):
        raise ValueError("scope manifest field 'exclusions' must be an object")

    python_scope = _read_path_list(audit, "python")
    json_scope = _read_path_list(audit, "json")
    python_watched_roots = _read_path_list(watched_roots, "python")
    json_watched_roots = _read_path_list(watched_roots, "json")
    python_exclusions = _read_exclusions(exclusions, "python")
    json_exclusions = _read_exclusions(exclusions, "json")

    _ensure_disjoint(python_scope, python_exclusions, "python")
    _ensure_disjoint(json_scope, json_exclusions, "json")

    return ScopeManifest(
        python_scope=python_scope,
        json_scope=json_scope,
        python_watched_roots=python_watched_roots,
        json_watched_roots=json_watched_roots,
        python_exclusions=python_exclusions,
        json_exclusions=json_exclusions,
    )


def _discover_scope_paths(repo_root: Path, roots: Sequence[str], suffix: str) -> Set[str]:
    discovered: Set[str] = set()
    for root in roots:
        root_path = repo_root / root
        if root_path.is_file() and root_path.suffix == suffix:
            discovered.add(root)
            continue
        if not root_path.is_dir():
            continue
        for path in root_path.rglob(f"*{suffix}"):
            if "__pycache__" in path.parts:
                continue
            discovered.add(path.relative_to(repo_root).as_posix())
    return discovered


def _scope_contract(repo_root: Path, manifest: ScopeManifest) -> Dict[str, Any]:
    python_declared = set(manifest.python_scope) | set(manifest.python_exclusions)
    json_declared = set(manifest.json_scope) | set(manifest.json_exclusions)
    python_discovered = _discover_scope_paths(repo_root, manifest.python_watched_roots, ".py")
    json_discovered = _discover_scope_paths(repo_root, manifest.json_watched_roots, ".json")

    undeclared_python = sorted(python_discovered - python_declared)
    undeclared_json = sorted(json_discovered - json_declared)
    return {
        "status": "PASS" if not (undeclared_python or undeclared_json) else "FAIL",
        "undeclared_paths": {
            "python": undeclared_python,
            "json": undeclared_json,
        },
        "declared_counts": {
            "python_audited": len(manifest.python_scope),
            "json_audited": len(manifest.json_scope),
            "python_excluded": len(manifest.python_exclusions),
            "json_excluded": len(manifest.json_exclusions),
        },
        "watched_counts": {
            "python": len(python_discovered),
            "json": len(json_discovered),
        },
    }


def _scan_python_literals(repo_root: Path, rel_path: str) -> List[NumericRef]:
    path = repo_root / rel_path
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    visitor = _ScopedNumericVisitor(rel_path, allowed_functions=PYTHON_REF_SCOPES.get(rel_path))
    visitor.visit(tree)
    visitor.items.sort(key=lambda item: item.ref)
    return visitor.items


def _walk_json(value: Any, path: str = "") -> Iterable[Tuple[str, float]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            next_path = f"{path}.{key}" if path else key
            yield from _walk_json(nested, next_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            next_path = f"{path}[{index}]"
            yield from _walk_json(nested, next_path)
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield (path, float(value))


def _collect_mission_schema_numeric_paths(schema: Mapping[str, Any]) -> Dict[str, float]:
    """Collect only numeric constraints tied to a concrete parameter_id."""

    out: Dict[str, float] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            parameter_id = node.get("parameter_id") if isinstance(node.get("parameter_id"), str) else None
            if parameter_id:
                for key in ("minimum", "maximum", "const", "multipleOf"):
                    raw = node.get(key)
                    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                        ref_path = f"{path}.{key}" if path else key
                        out[ref_path] = float(raw)
            for key, value in node.items():
                next_path = f"{path}.{key}" if path else key
                walk(value, next_path)
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                next_path = f"{path}[{index}]"
                walk(value, next_path)

    walk(schema, "")
    return out


def _scan_json_literals(repo_root: Path, rel_path: str) -> List[NumericRef]:
    path = repo_root / rel_path
    payload = load_json(path)
    refs: List[NumericRef] = []

    if rel_path == "mission/MISSION_SCHEMA_v1.json":
        filtered = _collect_mission_schema_numeric_paths(payload)
        for json_path, value in sorted(filtered.items()):
            refs.append(NumericRef(ref=f"{rel_path}#{json_path}", value=value, scope="json"))
        return refs

    for json_path, value in _walk_json(payload):
        refs.append(NumericRef(ref=f"{rel_path}#{json_path}", value=value, scope="json"))
    refs.sort(key=lambda item: item.ref)
    return refs


def _scan_scope(repo_root: Path, py_scope: Sequence[str], json_scope: Sequence[str]) -> List[NumericRef]:
    out: List[NumericRef] = []
    for rel in py_scope:
        out.extend(_scan_python_literals(repo_root, rel))
    for rel in json_scope:
        out.extend(_scan_json_literals(repo_root, rel))
    out.sort(key=lambda item: item.ref)
    return out


def _registry_refs(registry: Mapping[str, Any]) -> Tuple[Set[str], Set[str]]:
    parameters = registry.get("parameters")
    if not isinstance(parameters, list):
        return set(), set()

    code_refs: Set[str] = set()
    json_refs: Set[str] = set()
    for item in parameters:
        if not isinstance(item, dict):
            continue
        for ref in item.get("code_refs", []):
            if isinstance(ref, str) and ref.strip():
                code_refs.add(ref.strip())
        for ref in item.get("json_refs", []):
            if isinstance(ref, str) and ref.strip():
                json_refs.add(ref.strip())
    return code_refs, json_refs


def build_report(
    repo_root: Path,
    registry_path: Path,
    py_scope: Sequence[str] | None = None,
    json_scope: Sequence[str] | None = None,
    scope_manifest_path: Path = DEFAULT_SCOPE_MANIFEST,
) -> Dict[str, Any]:
    manifest = load_scope_manifest(repo_root, scope_manifest_path)
    if py_scope is None:
        py_scope = manifest.python_scope
    if json_scope is None:
        json_scope = manifest.json_scope

    registry = load_json(repo_root / registry_path)
    scanned = _scan_scope(repo_root, py_scope, json_scope)
    scope_contract = _scope_contract(repo_root, manifest)

    code_refs, json_refs = _registry_refs(registry)

    scanned_code = {item.ref for item in scanned if item.scope == "python"}
    scanned_json = {item.ref for item in scanned if item.scope == "json"}

    unmatched_code = sorted(scanned_code - code_refs)
    unmatched_json = sorted(scanned_json - json_refs)
    stale_code = sorted(code_refs - scanned_code)
    stale_json = sorted(json_refs - scanned_json)
    scope_violations = (
        scope_contract["undeclared_paths"]["python"] or scope_contract["undeclared_paths"]["json"]
    )

    report = {
        "status": "PASS"
        if not (unmatched_code or unmatched_json or stale_code or stale_json or scope_violations)
        else "FAIL",
        "scope": {
            "manifest": str(scope_manifest_path),
            "python": list(py_scope),
            "json": list(json_scope),
            "watched_roots": {
                "python": list(manifest.python_watched_roots),
                "json": list(manifest.json_watched_roots),
            },
            "excluded": {
                "python": {
                    path: {"rationale": rationale}
                    for path, rationale in sorted(manifest.python_exclusions.items())
                },
                "json": {
                    path: {"rationale": rationale}
                    for path, rationale in sorted(manifest.json_exclusions.items())
                },
            },
        },
        "scope_contract": scope_contract,
        "totals": {
            "literals_total": len(scanned),
            "python_literals": len(scanned_code),
            "json_literals": len(scanned_json),
            "matched_count": len(scanned) - len(unmatched_code) - len(unmatched_json),
            "unmatched_count": len(unmatched_code) + len(unmatched_json),
            "stale_registry_refs_count": len(stale_code) + len(stale_json),
        },
        "unmatched": {
            "python": unmatched_code,
            "json": unmatched_json,
        },
        "stale_registry_refs": {
            "python": stale_code,
            "json": stale_json,
        },
        "samples": [
            {
                "ref": item.ref,
                "value": item.value,
                "scope": item.scope,
            }
            for item in scanned[:200]
        ],
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--scope-manifest", default=str(DEFAULT_SCOPE_MANIFEST))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--format", choices=("text", "json"), default="json")
    return parser.parse_args()


def _render_text(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        f"{report['status']}: parameter literal scan",
        f"- literals_total: {totals['literals_total']}",
        f"- matched_count: {totals['matched_count']}",
        f"- unmatched_count: {totals['unmatched_count']}",
        f"- stale_registry_refs_count: {totals['stale_registry_refs_count']}",
    ]
    unmatched = report["unmatched"]
    stale = report["stale_registry_refs"]
    scope_contract = report["scope_contract"]
    if unmatched["python"] or unmatched["json"]:
        lines.append("- unmatched:")
        for ref in unmatched["python"]:
            lines.append(f"  - {ref}")
        for ref in unmatched["json"]:
            lines.append(f"  - {ref}")
    if stale["python"] or stale["json"]:
        lines.append("- stale_registry_refs:")
        for ref in stale["python"]:
            lines.append(f"  - {ref}")
        for ref in stale["json"]:
            lines.append(f"  - {ref}")
    undeclared = scope_contract["undeclared_paths"]
    if undeclared["python"] or undeclared["json"]:
        lines.append("- undeclared_scope_paths:")
        for ref in undeclared["python"]:
            lines.append(f"  - {ref}")
        for ref in undeclared["json"]:
            lines.append(f"  - {ref}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        report = build_report(
            repo_root=repo_root,
            registry_path=Path(args.registry),
            scope_manifest_path=Path(args.scope_manifest),
        )
        rendered = render_output(report, output_format=args.format, text_renderer=_render_text)
        print(rendered)
        if args.output:
            write_text(Path(args.output), rendered)

        if report["status"] == "PASS":
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
