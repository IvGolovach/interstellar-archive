#!/usr/bin/env python3
"""Build mission DAG dependency graph and detect cross-module hard dependencies."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set, Tuple

try:
    from .script_io import load_json, render_output, write_json, write_text
except ImportError:
    from script_io import load_json, render_output, write_json, write_text


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_MODULE_REGISTRY = Path("mission/dag/registry/module_registry.v1.json")
ALLOWED_INTERFACE_FILES = {
    "mission/dag/contracts.py",
    "mission/dag/hashchain.py",
}


@dataclass(frozen=True)
class ImportEdge:
    from_path: Path
    to_path: Path
    line: int
    raw: str

def _canonical(path: Path) -> str:
    return path.as_posix()


def _module_name_for_path(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root)
    if rel.name == "__init__.py":
        return ".".join(rel.parent.parts)
    return ".".join(rel.with_suffix("").parts)


def _path_for_module_name(repo_root: Path, module_name: str) -> Path | None:
    base = repo_root / Path(*module_name.split("."))
    py = base.with_suffix(".py")
    if py.exists():
        return py
    init = base / "__init__.py"
    if init.exists():
        return init
    return None


def _iter_mission_python_files(repo_root: Path) -> List[Path]:
    mission_root = repo_root / "mission"
    return sorted(path for path in mission_root.rglob("*.py") if path.is_file())


def _resolve_from_import_targets(
    *,
    repo_root: Path,
    current_module: str,
    node: ast.ImportFrom,
) -> List[Tuple[str, Path]]:
    targets: List[Tuple[str, Path]] = []

    if node.level > 0:
        current_parts = current_module.split(".")
        if node.level > len(current_parts):
            return targets
        base_parts = current_parts[:-node.level]
        if node.module:
            base_parts.extend(node.module.split("."))
        base_module = ".".join(part for part in base_parts if part)
    else:
        base_module = node.module or ""

    if not base_module:
        return targets

    # Always try base module itself first.
    base_path = _path_for_module_name(repo_root, base_module)
    if base_module.startswith("mission") and base_path is not None:
        targets.append((base_module, base_path))

    for alias in node.names:
        if alias.name == "*":
            continue
        candidate = f"{base_module}.{alias.name}"
        candidate_path = _path_for_module_name(repo_root, candidate)
        if candidate.startswith("mission") and candidate_path is not None:
            targets.append((candidate, candidate_path))

    return targets


def _parse_import_edges(repo_root: Path) -> Tuple[List[ImportEdge], Dict[str, str], Dict[str, List[str]]]:
    files = _iter_mission_python_files(repo_root)
    path_to_module: Dict[str, str] = {}
    dep_map: Dict[str, List[str]] = {}
    edges: List[ImportEdge] = []

    for path in files:
        module_name = _module_name_for_path(repo_root, path)
        path_key = _canonical(path.relative_to(repo_root))
        path_to_module[path_key] = module_name
        dep_map.setdefault(path_key, [])

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if not name.startswith("mission"):
                        continue
                    target_path = _path_for_module_name(repo_root, name)
                    if target_path is None:
                        continue
                    target_key = _canonical(target_path.relative_to(repo_root))
                    dep_map[path_key].append(target_key)
                    edges.append(
                        ImportEdge(
                            from_path=path,
                            to_path=target_path,
                            line=int(getattr(node, "lineno", 0)),
                            raw=f"import {name}",
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                targets = _resolve_from_import_targets(
                    repo_root=repo_root,
                    current_module=module_name,
                    node=node,
                )
                for target_module, target_path in targets:
                    target_key = _canonical(target_path.relative_to(repo_root))
                    dep_map[path_key].append(target_key)
                    edges.append(
                        ImportEdge(
                            from_path=path,
                            to_path=target_path,
                            line=int(getattr(node, "lineno", 0)),
                            raw=f"from {target_module} import ...",
                        )
                    )

    for key, deps in dep_map.items():
        dep_map[key] = sorted(set(deps))
    return edges, path_to_module, dep_map


def _find_cycles(dep_map: Mapping[str, Sequence[str]]) -> List[List[str]]:
    cycles: List[List[str]] = []
    temporary: Set[str] = set()
    permanent: Set[str] = set()
    stack: List[str] = []

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            if node in stack:
                index = stack.index(node)
                cycles.append(stack[index:] + [node])
            return
        temporary.add(node)
        stack.append(node)
        for dep in dep_map.get(node, []):
            if dep in dep_map:
                visit(dep)
        stack.pop()
        temporary.remove(node)
        permanent.add(node)

    for node in sorted(dep_map):
        visit(node)

    normalized: List[List[str]] = []
    seen: Set[Tuple[str, ...]] = set()
    for cycle in cycles:
        core = cycle[:-1]
        if not core:
            continue
        min_index = min(range(len(core)), key=lambda idx: core[idx])
        rotated = core[min_index:] + core[:min_index]
        key = tuple(rotated)
        if key not in seen:
            seen.add(key)
            normalized.append(rotated)
    return sorted(normalized)


def _load_module_entrypoints(repo_root: Path, module_registry_path: Path) -> List[Dict[str, str]]:
    registry = load_json(repo_root / module_registry_path)
    modules = registry.get("modules", [])
    out: List[Dict[str, str]] = []
    for module in modules:
        if not isinstance(module, Mapping):
            continue
        entrypoint = module.get("implemented_by", {}).get("python_entrypoint")
        if not isinstance(entrypoint, str) or ":" not in entrypoint:
            continue
        path_part, func_part = entrypoint.split(":", 1)
        out.append(
            {
                "module_id": str(module.get("module_id", "")),
                "module_type": str(module.get("module_type", "")),
                "path": path_part,
                "function": func_part,
            }
        )
    return out


def _find_function_defs(path: Path) -> Dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    defs: Dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defs[node.name] = node
    return defs


def _find_hard_dependencies(
    *,
    repo_root: Path,
    module_registry_path: Path,
    edges: Sequence[ImportEdge],
) -> List[Dict[str, Any]]:
    hard: List[Dict[str, Any]] = []
    entrypoints = _load_module_entrypoints(repo_root, module_registry_path)
    module_by_file: Dict[str, List[Dict[str, str]]] = {}
    for entry in entrypoints:
        module_by_file.setdefault(entry["path"], []).append(entry)

    allowed = set(ALLOWED_INTERFACE_FILES)

    for edge in edges:
        from_rel = _canonical(edge.from_path.relative_to(repo_root))
        to_rel = _canonical(edge.to_path.relative_to(repo_root))
        from_modules = module_by_file.get(from_rel, [])
        to_modules = module_by_file.get(to_rel, [])
        if not from_modules or not to_modules:
            continue
        for src in from_modules:
            for dst in to_modules:
                if src["module_id"] == dst["module_id"]:
                    continue
                if to_rel in allowed:
                    continue
                hard.append(
                    {
                        "type": "cross_module_import",
                        "from_module_id": src["module_id"],
                        "to_module_id": dst["module_id"],
                        "file": from_rel,
                        "line": edge.line,
                        "detail": edge.raw,
                    }
                )

    # Detect direct calls between module entrypoint functions (same file bypass).
    functions_by_name = {entry["function"]: entry for entry in entrypoints}
    for file_rel, entries in module_by_file.items():
        file_path = repo_root / file_rel
        defs = _find_function_defs(file_path)
        for entry in entries:
            func_name = entry["function"]
            fn = defs.get(func_name)
            if fn is None:
                continue
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                called_name: str | None = None
                if isinstance(node.func, ast.Name):
                    called_name = node.func.id
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    called_name = f"{node.func.value.id}.{node.func.attr}"

                if called_name is None:
                    continue
                target = functions_by_name.get(called_name)
                if target is None and "." in called_name:
                    target = functions_by_name.get(called_name.split(".", 1)[1])
                if target is None:
                    continue
                if target["module_id"] == entry["module_id"]:
                    continue
                hard.append(
                    {
                        "type": "direct_module_call",
                        "from_module_id": entry["module_id"],
                        "to_module_id": target["module_id"],
                        "file": file_rel,
                        "line": int(getattr(node, "lineno", 0)),
                        "detail": called_name,
                    }
                )

    return hard


def analyze(repo_root: Path, module_registry_path: Path) -> Dict[str, Any]:
    edges, path_to_module, dep_map = _parse_import_edges(repo_root)
    cycle_dep_map: Dict[str, List[str]] = {}
    for node, deps in dep_map.items():
        if node.endswith("__init__.py"):
            continue
        filtered = [dep for dep in deps if not dep.endswith("__init__.py")]
        cycle_dep_map[node] = filtered

    cycles = _find_cycles(cycle_dep_map)
    hard = _find_hard_dependencies(
        repo_root=repo_root,
        module_registry_path=module_registry_path,
        edges=edges,
    )

    entrypoints = _load_module_entrypoints(repo_root, module_registry_path)
    status = "PASS" if not cycles and not hard else "FAIL"
    return {
        "status": status,
        "summary": {
            "python_file_count": len(path_to_module),
            "import_edge_count": len(edges),
            "cycle_count": len(cycles),
            "hard_dependency_count": len(hard),
            "entrypoint_module_count": len(entrypoints),
        },
        "allowed_interface_files": sorted(ALLOWED_INTERFACE_FILES),
        "entrypoints": entrypoints,
        "graph": {
            "nodes": [{"path": path, "module": module} for path, module in sorted(path_to_module.items())],
            "edges": [
                {
                    "from": _canonical(edge.from_path.relative_to(repo_root)),
                    "to": _canonical(edge.to_path.relative_to(repo_root)),
                    "line": edge.line,
                    "import": edge.raw,
                }
                for edge in edges
            ],
            "cycles": cycles,
        },
        "hard_dependencies": hard,
    }


def _render_markdown(result: Mapping[str, Any]) -> str:
    lines: List[str] = [
        "# Module Dependency Graph Audit",
        "",
        f"- status: `{result['status']}`",
        f"- python files: `{result['summary']['python_file_count']}`",
        f"- import edges: `{result['summary']['import_edge_count']}`",
        f"- cycles: `{result['summary']['cycle_count']}`",
        f"- hard dependencies: `{result['summary']['hard_dependency_count']}`",
        "",
        "## Entrypoints",
        "",
        "| Module ID | Module Type | Entrypoint |",
        "|---|---|---|",
    ]
    for entry in result.get("entrypoints", []):
        lines.append(f"| {entry['module_id']} | {entry['module_type']} | {entry['path']}:{entry['function']} |")

    lines.extend(["", "## Cycles", ""])
    cycles = result.get("graph", {}).get("cycles", [])
    if not cycles:
        lines.append("- none")
    else:
        for cycle in cycles:
            lines.append(f"- {' -> '.join(cycle)}")

    lines.extend(["", "## Hard Dependencies", ""])
    hard = result.get("hard_dependencies", [])
    if not hard:
        lines.append("- none")
    else:
        for item in hard:
            lines.append(
                "- `{type}` {from_module_id} -> {to_module_id} at `{file}:{line}` (`{detail}`)".format(
                    **item
                )
            )

    lines.extend(["", "## Allowed Interfaces", ""])
    for path in result.get("allowed_interface_files", []):
        lines.append(f"- `{path}`")
    return "\n".join(lines) + "\n"


def _render_text(result: Mapping[str, Any]) -> str:
    lines = [
        f"{result['status']}: dag dependency graph",
        f"- python_files: {result['summary']['python_file_count']}",
        f"- import_edges: {result['summary']['import_edge_count']}",
        f"- cycles: {result['summary']['cycle_count']}",
        f"- hard_dependencies: {result['summary']['hard_dependency_count']}",
    ]
    if result["hard_dependencies"]:
        lines.append("- hard_dependency_samples:")
        for item in result["hard_dependencies"][:5]:
            lines.append(
                "  - {type}: {from_module_id}->{to_module_id} at {file}:{line}".format(
                    **item
                )
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--module-registry", default=str(DEFAULT_MODULE_REGISTRY))
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        result = analyze(repo_root=repo_root, module_registry_path=Path(args.module_registry))

        if args.json_out:
            write_json(Path(args.json_out), result)
        if args.md_out:
            write_text(Path(args.md_out), _render_markdown(result))

        print(render_output(result, output_format=args.format, text_renderer=_render_text))

        if result["status"] == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        print(f"INTERNAL ERROR: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
