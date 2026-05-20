"""Importable mission evidence validator and governance checks."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


EXIT_PASS = 0
EXIT_VIOLATION = 2
EXIT_INTERNAL = 3

DEFAULT_EVIDENCE_SCHEMA = Path("mission/EVIDENCE_SCHEMA_v1.json")
DEFAULT_EVIDENCE_REGISTRY = Path("mission/EVIDENCE_REGISTRY_v1.json")
DEFAULT_MISSION_SCHEMA = Path("mission/MISSION_SCHEMA_v1.json")
DEFAULT_UNCERTAINTY_MODEL = Path("mission/UNCERTAINTY_MODEL_v1.json")
DEFAULT_CHANGELOG = Path("engineering/CHANGELOG.md")
ALLOWED_SOURCE_TYPES = {"paper", "report", "dataset", "assumption"}
ALLOWED_MODES = {"realistic", "speculative"}
ALLOWED_VALUE_MODES = {"scalar", "distribution"}
ALLOWED_TRUST = {"A", "B", "C", "D"}


class EvidenceValidationError(RuntimeError):
    """Raised for internal validator errors."""


@dataclass
class ValidationResult:
    status: str
    errors: List[str]
    notes: List[str]
    total_parameters: int
    missing_evidence_count: int
    realistic_d_violations: int
    trust_distribution: Dict[str, int]
    evidence_completeness_ratio: float
    drift_guard_checked: bool
    drift_guard_triggered: bool


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _round_ratio(value: float) -> float:
    return float(f"{value:.6f}")


def _run_git(repo_root: Path, args: Sequence[str], allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 and not allow_failure:
        raise EvidenceValidationError(
            f"git {' '.join(args)} failed with code {proc.returncode}: "
            f"{proc.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return proc


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceValidationError(f"missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceValidationError(f"invalid JSON in {path}: {exc}") from exc


def _validate_evidence_schema_document(schema: Mapping[str, Any], errors: List[str]) -> None:
    required_top = {"schema_version", "evidence_sources", "parameter_claims"}
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        errors.append("EVIDENCE_SCHEMA missing $defs object.")
        return

    if schema.get("type") != "object":
        errors.append("EVIDENCE_SCHEMA root type must be object.")
    if not required_top.issubset(set(schema.get("required", []))):
        errors.append("EVIDENCE_SCHEMA required list missing schema_version/evidence_sources/parameter_claims.")

    source_def = defs.get("EvidenceSource")
    claim_def = defs.get("ParameterClaim")
    if not isinstance(source_def, dict):
        errors.append("EVIDENCE_SCHEMA missing $defs.EvidenceSource.")
    else:
        source_required = {"id", "type", "citation", "url", "claim_scope", "notes"}
        if not source_required.issubset(set(source_def.get("required", []))):
            errors.append("EVIDENCE_SCHEMA EvidenceSource missing required fields.")

    if not isinstance(claim_def, dict):
        errors.append("EVIDENCE_SCHEMA missing $defs.ParameterClaim.")
    else:
        claim_required = {
            "parameter_id",
            "value_mode",
            "units",
            "mode",
            "evidence_source_ids",
            "trust_grade",
            "justification",
            "last_reviewed_commit",
        }
        if not claim_required.issubset(set(claim_def.get("required", []))):
            errors.append("EVIDENCE_SCHEMA ParameterClaim missing required fields.")

        all_of = claim_def.get("allOf")
        if not isinstance(all_of, list) or len(all_of) < 2:
            errors.append("EVIDENCE_SCHEMA ParameterClaim must encode mode/trust rules in allOf.")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) > 0


def _iter_parameter_ids(schema: Any) -> Iterable[str]:
    if isinstance(schema, dict):
        parameter_id = schema.get("parameter_id")
        if isinstance(parameter_id, str):
            yield parameter_id
        for value in schema.values():
            yield from _iter_parameter_ids(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _iter_parameter_ids(value)


def _collect_schema_parameter_ids(mission_schema: Mapping[str, Any]) -> Set[str]:
    return set(_iter_parameter_ids(mission_schema))


def _validate_uncertainty_model(uncertainty_model: Mapping[str, Any], errors: List[str]) -> Dict[str, Dict[str, Any]]:
    entries = uncertainty_model.get("entries")
    if not isinstance(entries, list) or len(entries) == 0:
        errors.append("UNCERTAINTY_MODEL entries must be a non-empty array.")
        return {}

    by_parameter: Dict[str, Dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        prefix = f"uncertainty.entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        parameter_id = entry.get("parameter_id")
        if not _is_non_empty_string(parameter_id):
            errors.append(f"{prefix}.parameter_id must be non-empty string.")
            continue

        distribution = entry.get("distribution")
        if distribution not in {"normal", "lognormal", "uniform", "triangular"}:
            errors.append(f"{prefix}.distribution '{distribution}' is invalid.")

        parameters = entry.get("parameters")
        if not isinstance(parameters, dict) or len(parameters) == 0:
            errors.append(f"{prefix}.parameters must be non-empty object.")

        bounds = entry.get("bounds")
        if not isinstance(bounds, dict):
            errors.append(f"{prefix}.bounds must be object.")
        else:
            low = bounds.get("min")
            high = bounds.get("max")
            if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                errors.append(f"{prefix}.bounds requires numeric min and max.")
            elif float(low) >= float(high):
                errors.append(f"{prefix}.bounds requires min < max.")

        units = entry.get("units")
        if not _is_non_empty_string(units):
            errors.append(f"{prefix}.units must be non-empty string.")

        by_parameter[str(parameter_id)] = entry
    return by_parameter


def _validate_registry(
    registry: Mapping[str, Any],
    required_parameter_ids: Set[str],
    uncertainty_by_parameter: Mapping[str, Dict[str, Any]],
    errors: List[str],
) -> Tuple[Dict[str, int], int, int, float]:
    sources = registry.get("evidence_sources")
    claims = registry.get("parameter_claims")
    if registry.get("schema_version") != "evidence_registry.v1":
        errors.append("registry.schema_version must be evidence_registry.v1.")

    if not isinstance(sources, list) or len(sources) == 0:
        errors.append("registry.evidence_sources must be a non-empty array.")
        return {"A": 0, "B": 0, "C": 0, "D": 0}, 0, 0, 0.0
    if not isinstance(claims, list) or len(claims) == 0:
        errors.append("registry.parameter_claims must be a non-empty array.")
        return {"A": 0, "B": 0, "C": 0, "D": 0}, len(required_parameter_ids), 0, 0.0

    source_ids: Set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"evidence_sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be object.")
            continue
        source_id = source.get("id")
        if not _is_non_empty_string(source_id):
            errors.append(f"{prefix}.id must be non-empty string.")
            continue
        if source_id in source_ids:
            errors.append(f"{prefix}.id '{source_id}' is duplicated.")
        source_ids.add(str(source_id))
        if source.get("type") not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}.type '{source.get('type')}' is invalid.")
        for field in ["citation", "claim_scope", "notes"]:
            if not _is_non_empty_string(source.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty string.")
        url = source.get("url")
        if url is not None and not _is_non_empty_string(url):
            errors.append(f"{prefix}.url must be string|null.")

    seen_parameter_ids: Set[str] = set()
    trust_distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    realistic_d_violations = 0
    for index, claim in enumerate(claims):
        prefix = f"parameter_claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be object.")
            continue

        parameter_id = claim.get("parameter_id")
        if not _is_non_empty_string(parameter_id):
            errors.append(f"{prefix}.parameter_id must be non-empty string.")
            continue
        parameter_id = str(parameter_id)
        if parameter_id in seen_parameter_ids:
            errors.append(f"{prefix}.parameter_id '{parameter_id}' is duplicated.")
        seen_parameter_ids.add(parameter_id)

        value_mode = claim.get("value_mode")
        if value_mode not in ALLOWED_VALUE_MODES:
            errors.append(f"{prefix}.value_mode '{value_mode}' is invalid.")

        units = claim.get("units")
        if not _is_non_empty_string(units):
            errors.append(f"{prefix}.units must be non-empty string.")

        mode = claim.get("mode")
        if mode not in ALLOWED_MODES:
            errors.append(f"{prefix}.mode '{mode}' is invalid.")

        source_ref_ids = claim.get("evidence_source_ids")
        if not isinstance(source_ref_ids, list) or len(source_ref_ids) == 0:
            errors.append(f"{prefix}.evidence_source_ids must be non-empty array.")
            source_ref_ids = []
        else:
            for src in source_ref_ids:
                if not _is_non_empty_string(src):
                    errors.append(f"{prefix}.evidence_source_ids has invalid id.")
                elif src not in source_ids:
                    errors.append(f"{prefix}.evidence_source_ids contains unknown source '{src}'.")

        trust_grade = claim.get("trust_grade")
        if trust_grade not in ALLOWED_TRUST:
            errors.append(f"{prefix}.trust_grade '{trust_grade}' is invalid.")
            trust_grade = None
        if trust_grade is not None:
            trust_distribution[trust_grade] += 1

        if mode == "realistic" and trust_grade == "D":
            realistic_d_violations += 1
            errors.append(f"{prefix}: realistic mode cannot use trust_grade D.")
        if trust_grade == "D" and mode != "speculative":
            errors.append(f"{prefix}: trust_grade D is allowed only for speculative mode.")

        if not _is_non_empty_string(claim.get("justification")):
            errors.append(f"{prefix}.justification must be non-empty string.")
        if not _is_non_empty_string(claim.get("last_reviewed_commit")):
            errors.append(f"{prefix}.last_reviewed_commit must be non-empty string.")

        if value_mode == "distribution":
            uncertainty_entry = uncertainty_by_parameter.get(parameter_id)
            if uncertainty_entry is None:
                errors.append(f"{prefix}: distribution claim requires uncertainty entry for '{parameter_id}'.")
            else:
                bounds = uncertainty_entry.get("bounds")
                if not isinstance(bounds, dict):
                    errors.append(f"{prefix}: uncertainty bounds missing for '{parameter_id}'.")
                else:
                    low = bounds.get("min")
                    high = bounds.get("max")
                    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)) or float(low) >= float(high):
                        errors.append(f"{prefix}: uncertainty bounds invalid for '{parameter_id}'.")

    missing_parameter_ids = sorted(required_parameter_ids - seen_parameter_ids)
    if missing_parameter_ids:
        errors.append("missing parameter claims for: " + ", ".join(missing_parameter_ids))

    total_parameters = len(required_parameter_ids)
    missing_count = len(missing_parameter_ids)
    completeness_ratio = 1.0 if total_parameters == 0 else (total_parameters - missing_count) / total_parameters
    return trust_distribution, total_parameters, missing_count, _round_ratio(completeness_ratio)


def _decode_utf8_bytes(payload: bytes, context: str) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceValidationError(f"{context} is not valid UTF-8") from exc


def _claim_key_map(registry: Mapping[str, Any]) -> Dict[str, str]:
    claims = registry.get("parameter_claims", [])
    out: Dict[str, str] = {}
    if not isinstance(claims, list):
        return out
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            out[str(claim["parameter_id"])] = _canonical_json(claim)
    return out


def _trust_and_source_map(registry: Mapping[str, Any]) -> Dict[str, Tuple[str, Tuple[str, ...]]]:
    claims = registry.get("parameter_claims", [])
    out: Dict[str, Tuple[str, Tuple[str, ...]]] = {}
    if not isinstance(claims, list):
        return out
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("parameter_id"), str):
            pid = str(claim["parameter_id"])
            trust = str(claim.get("trust_grade", ""))
            srcs = claim.get("evidence_source_ids", [])
            src_tuple: Tuple[str, ...]
            if isinstance(srcs, list):
                src_tuple = tuple(sorted(str(item) for item in srcs))
            else:
                src_tuple = tuple()
            out[pid] = (trust, src_tuple)
    return out


def _file_at_ref(repo_root: Path, ref: str, rel_path: Path) -> Optional[Dict[str, Any]]:
    proc = _run_git(repo_root, ["show", f"{ref}:{rel_path.as_posix()}"], allow_failure=True)
    if proc.returncode != 0:
        return None
    text = _decode_utf8_bytes(proc.stdout, f"{ref}:{rel_path.as_posix()}")
    return json.loads(text)


def _changed_paths(repo_root: Path, base: Optional[str], head: Optional[str]) -> Set[str]:
    if base and head:
        proc = _run_git(repo_root, ["diff", "--name-only", base, head], allow_failure=False)
    else:
        proc = _run_git(repo_root, ["diff", "--name-only", "HEAD"], allow_failure=False)
    text = _decode_utf8_bytes(proc.stdout, "git diff --name-only output")
    return {line.strip() for line in text.splitlines() if line.strip()}


def _enforce_drift_guard(
    repo_root: Path,
    registry_path: Path,
    changelog_path: Path,
    current_registry: Mapping[str, Any],
    base: Optional[str],
    head: Optional[str],
    errors: List[str],
    notes: List[str],
) -> bool:
    changed = _changed_paths(repo_root, base, head)
    registry_rel = registry_path.as_posix()
    changelog_rel = changelog_path.as_posix()
    if registry_rel not in changed:
        notes.append("drift guard: registry unchanged in diff range.")
        return False

    previous_registry: Optional[Dict[str, Any]]
    if base:
        previous_registry = _file_at_ref(repo_root, base, registry_path)
    else:
        previous_registry = _file_at_ref(repo_root, "HEAD", registry_path)
    if previous_registry is None:
        notes.append("drift guard: no previous registry found; skipping changelog trigger check.")
        return True

    current_claim_map = _claim_key_map(current_registry)
    previous_claim_map = _claim_key_map(previous_registry)
    current_trust_src = _trust_and_source_map(current_registry)
    previous_trust_src = _trust_and_source_map(previous_registry)

    any_claim_changed = current_claim_map != previous_claim_map
    any_trust_or_sources_changed = current_trust_src != previous_trust_src
    trigger = any_claim_changed or any_trust_or_sources_changed

    if trigger and changelog_rel not in changed:
        errors.append(
            "registry claims changed (ParameterClaim/trust_grade/evidence_source_ids), "
            "but engineering/CHANGELOG.md was not updated."
        )
    elif trigger:
        notes.append("drift guard: registry changes detected and changelog updated.")
    else:
        notes.append("drift guard: registry file changed without claim-level drift.")

    return True


def run_validation(
    repo_root: Path,
    evidence_schema_path: Path,
    evidence_registry_path: Path,
    mission_schema_path: Path,
    uncertainty_model_path: Path,
    changelog_path: Path,
    base: Optional[str],
    head: Optional[str],
) -> ValidationResult:
    errors: List[str] = []
    notes: List[str] = []

    evidence_schema = _load_json(repo_root / evidence_schema_path)
    evidence_registry = _load_json(repo_root / evidence_registry_path)
    mission_schema = _load_json(repo_root / mission_schema_path)
    uncertainty_model = _load_json(repo_root / uncertainty_model_path)

    _validate_evidence_schema_document(evidence_schema, errors)
    required_parameter_ids = _collect_schema_parameter_ids(mission_schema)
    uncertainty_by_parameter = _validate_uncertainty_model(uncertainty_model, errors)
    trust_distribution, total_parameters, missing_count, completeness_ratio = _validate_registry(
        evidence_registry,
        required_parameter_ids,
        uncertainty_by_parameter,
        errors,
    )

    realistic_d_violations = sum(
        1
        for claim in evidence_registry.get("parameter_claims", [])
        if isinstance(claim, dict) and claim.get("mode") == "realistic" and claim.get("trust_grade") == "D"
    )

    drift_checked = _enforce_drift_guard(
        repo_root=repo_root,
        registry_path=evidence_registry_path,
        changelog_path=changelog_path,
        current_registry=evidence_registry,
        base=base,
        head=head,
        errors=errors,
        notes=notes,
    )

    status = "PASS" if not errors else "FAIL"
    return ValidationResult(
        status=status,
        errors=errors,
        notes=notes,
        total_parameters=total_parameters,
        missing_evidence_count=missing_count,
        realistic_d_violations=realistic_d_violations,
        trust_distribution=trust_distribution,
        evidence_completeness_ratio=completeness_ratio,
        drift_guard_checked=True,
        drift_guard_triggered=drift_checked,
    )


def _render_text(result: ValidationResult) -> str:
    lines = [
        f"{result.status}: evidence contract validation",
        f"- total_parameters: {result.total_parameters}",
        f"- missing_evidence_count: {result.missing_evidence_count}",
        f"- realistic_D_violations: {result.realistic_d_violations}",
        f"- evidence_completeness_ratio: {result.evidence_completeness_ratio:.6f}",
        "- trust_distribution: "
        + ", ".join(f"{grade}={result.trust_distribution.get(grade, 0)}" for grade in ["A", "B", "C", "D"]),
    ]
    if result.notes:
        lines.append("- notes:")
        for note in result.notes:
            lines.append(f"  - {note}")
    if result.errors:
        lines.append("- errors:")
        for error in result.errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def _render_json(result: ValidationResult) -> str:
    payload = {
        "status": result.status,
        "total_parameters": result.total_parameters,
        "missing_evidence_count": result.missing_evidence_count,
        "realistic_D_violations": result.realistic_d_violations,
        "evidence_completeness_ratio": result.evidence_completeness_ratio,
        "trust_distribution": result.trust_distribution,
        "drift_guard_checked": result.drift_guard_checked,
        "drift_guard_triggered": result.drift_guard_triggered,
        "notes": result.notes,
        "errors": result.errors,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit code on violations")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", help="Optional path to save validator output")
    parser.add_argument("--base", help="Optional base commit SHA for drift diff")
    parser.add_argument("--head", help="Optional head commit SHA for drift diff")
    return parser.parse_args()


def _write_output(path: Path, payload: str) -> None:
    path.write_text(payload + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        result = run_validation(
            repo_root=repo_root,
            evidence_schema_path=DEFAULT_EVIDENCE_SCHEMA,
            evidence_registry_path=DEFAULT_EVIDENCE_REGISTRY,
            mission_schema_path=DEFAULT_MISSION_SCHEMA,
            uncertainty_model_path=DEFAULT_UNCERTAINTY_MODEL,
            changelog_path=DEFAULT_CHANGELOG,
            base=args.base,
            head=args.head,
        )
        rendered = _render_json(result) if args.format == "json" else _render_text(result)
        print(rendered)
        if args.output:
            _write_output(Path(args.output), rendered)
        if result.status == "PASS":
            return EXIT_PASS
        return EXIT_VIOLATION if args.strict else EXIT_PASS
    except Exception as exc:  # noqa: BLE001
        message = f"INTERNAL ERROR: {exc}"
        print(message)
        if args.output:
            _write_output(Path(args.output), message)
        return EXIT_INTERNAL
