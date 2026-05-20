from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from mission import evidence_validation as evidence_validate


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "evidence_validate.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _copy_contract_files(target_root: Path) -> None:
    (target_root / "mission").mkdir(parents=True, exist_ok=True)
    (target_root / "engineering").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "mission" / "EVIDENCE_SCHEMA_v1.json", target_root / "mission" / "EVIDENCE_SCHEMA_v1.json")
    shutil.copyfile(REPO_ROOT / "mission" / "EVIDENCE_REGISTRY_v1.json", target_root / "mission" / "EVIDENCE_REGISTRY_v1.json")
    shutil.copyfile(REPO_ROOT / "mission" / "MISSION_SCHEMA_v1.json", target_root / "mission" / "MISSION_SCHEMA_v1.json")
    shutil.copyfile(REPO_ROOT / "mission" / "UNCERTAINTY_MODEL_v1.json", target_root / "mission" / "UNCERTAINTY_MODEL_v1.json")
    (target_root / "engineering" / "CHANGELOG.md").write_text("## baseline\n", encoding="utf-8")


def _init_git_repo(repo_root: Path) -> str:
    _run(["git", "init"], cwd=repo_root)
    _run(["git", "config", "user.email", "tests@example.com"], cwd=repo_root)
    _run(["git", "config", "user.name", "Evidence Tests"], cwd=repo_root)
    _run(["git", "add", "."], cwd=repo_root)
    commit = _run(["git", "commit", "-m", "fixture"], cwd=repo_root)
    if commit.returncode != 0:
        raise AssertionError(commit.stdout + commit.stderr)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    return head


class EvidenceContractTests(unittest.TestCase):
    def test_current_repo_contract_passes(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        proc = _run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repo-root",
                str(REPO_ROOT),
                "--strict",
                "--base",
                head,
                "--head",
                head,
            ],
            cwd=REPO_ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_schema_document_validation_detects_missing_defs(self) -> None:
        errors: list[str] = []
        evidence_validate._validate_evidence_schema_document(  # pylint: disable=protected-access
            {"type": "object", "required": []},
            errors,
        )
        self.assertTrue(errors)
        self.assertTrue(any("missing $defs" in item for item in errors))

    def test_uncertainty_validator_catches_bad_bounds(self) -> None:
        errors: list[str] = []
        out = evidence_validate._validate_uncertainty_model(  # pylint: disable=protected-access
            {
                "entries": [
                    {
                        "parameter_id": "trajectory_model.nav_position_sigma_m",
                        "distribution": "normal",
                        "parameters": {"mean": 0, "sigma": 1},
                        "bounds": {"min": 10, "max": 10},
                        "units": "m",
                    }
                ]
            },
            errors,
        )
        self.assertIn("trajectory_model.nav_position_sigma_m", out)
        self.assertTrue(any("min < max" in item for item in errors))

    def test_load_json_error_paths_and_run_git_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with self.assertRaises(evidence_validate.EvidenceValidationError):
                evidence_validate._load_json(root / "missing.json")  # pylint: disable=protected-access

            bad = root / "bad.json"
            bad.write_text("{bad", encoding="utf-8")
            with self.assertRaises(evidence_validate.EvidenceValidationError):
                evidence_validate._load_json(bad)  # pylint: disable=protected-access

            with self.assertRaises(evidence_validate.EvidenceValidationError):
                evidence_validate._run_git(root, ["status"], allow_failure=False)  # pylint: disable=protected-access

    def test_drift_guard_requires_changelog_on_claim_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            _copy_contract_files(repo)
            _init_git_repo(repo)

            registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            claim = registry["parameter_claims"][0]
            original = claim.get("trust_grade")
            claim["trust_grade"] = "C" if original != "C" else "B"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

            proc = _run([sys.executable, str(VALIDATOR), "--repo-root", str(repo), "--strict"], cwd=repo)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("CHANGELOG", proc.stdout)

    def test_drift_guard_passes_when_changelog_updated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            _copy_contract_files(repo)
            _init_git_repo(repo)

            registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["parameter_claims"][0]["justification"] = "Updated rationale for deterministic test."
            registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

            changelog_path = repo / "engineering" / "CHANGELOG.md"
            changelog_path.write_text(changelog_path.read_text(encoding="utf-8") + "\n- evidence claim update\n", encoding="utf-8")

            proc = _run([sys.executable, str(VALIDATOR), "--repo-root", str(repo), "--strict"], cwd=repo)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("PASS", proc.stdout)

    def test_helper_functions_and_renderers(self) -> None:
        # _decode_utf8_bytes valid + invalid.
        self.assertEqual("ok", evidence_validate._decode_utf8_bytes(b"ok", "ctx"))  # pylint: disable=protected-access
        with self.assertRaises(evidence_validate.EvidenceValidationError):
            evidence_validate._decode_utf8_bytes(b"\xff", "ctx")  # pylint: disable=protected-access

        # _claim_key_map / _trust_and_source_map non-list fallback.
        self.assertEqual({}, evidence_validate._claim_key_map({"parameter_claims": "bad"}))  # pylint: disable=protected-access
        self.assertEqual({}, evidence_validate._trust_and_source_map({"parameter_claims": None}))  # pylint: disable=protected-access

        # _render_text / _render_json should include status and counters.
        result = evidence_validate.ValidationResult(
            status="PASS",
            errors=[],
            notes=["note"],
            total_parameters=2,
            missing_evidence_count=0,
            realistic_d_violations=0,
            trust_distribution={"A": 1, "B": 0, "C": 1, "D": 0},
            evidence_completeness_ratio=1.0,
            drift_guard_checked=True,
            drift_guard_triggered=False,
        )
        rendered_text = evidence_validate._render_text(result)  # pylint: disable=protected-access
        rendered_json = evidence_validate._render_json(result)  # pylint: disable=protected-access
        self.assertIn("PASS", rendered_text)
        self.assertIn("\"status\": \"PASS\"", rendered_json)

    def test_registry_and_uncertainty_edge_validation(self) -> None:
        errors: list[str] = []
        uncertainty = evidence_validate._validate_uncertainty_model(  # pylint: disable=protected-access
            {"entries": [{"parameter_id": "", "distribution": "bad", "parameters": {}, "bounds": {"min": 2, "max": 1}, "units": ""}]},
            errors,
        )
        self.assertTrue(errors)
        self.assertEqual({}, uncertainty)

        errors2: list[str] = []
        trust, total, missing, ratio = evidence_validate._validate_registry(  # pylint: disable=protected-access
            registry={
                "schema_version": "wrong",
                "evidence_sources": [{"id": "SRC-A", "type": "bad", "citation": "", "url": 1, "claim_scope": "", "notes": ""}],
                "parameter_claims": [
                    {
                        "parameter_id": "",
                        "value_mode": "bad",
                        "units": "",
                        "mode": "realistic",
                        "evidence_source_ids": [],
                        "trust_grade": "Z",
                        "justification": "",
                        "last_reviewed_commit": "",
                    }
                ],
            },
            required_parameter_ids={"p1"},
            uncertainty_by_parameter={},
            errors=errors2,
        )
        self.assertTrue(errors2)
        self.assertEqual(total, 1)
        self.assertEqual(missing, 1)
        self.assertLess(ratio, 1.0)
        self.assertEqual(set(trust.keys()), {"A", "B", "C", "D"})

        # Early-return branches.
        errors3: list[str] = []
        trust3, total3, missing3, ratio3 = evidence_validate._validate_registry(  # pylint: disable=protected-access
            registry={"schema_version": "evidence_registry.v1", "evidence_sources": [], "parameter_claims": []},
            required_parameter_ids=set(),
            uncertainty_by_parameter={},
            errors=errors3,
        )
        self.assertEqual(trust3, {"A": 0, "B": 0, "C": 0, "D": 0})
        self.assertEqual(total3, 0)
        self.assertEqual(missing3, 0)
        self.assertEqual(ratio3, 0.0)
        self.assertTrue(any("evidence_sources must be a non-empty array" in item for item in errors3))

        errors4: list[str] = []
        trust4, total4, missing4, ratio4 = evidence_validate._validate_registry(  # pylint: disable=protected-access
            registry={"schema_version": "evidence_registry.v1", "evidence_sources": [{}], "parameter_claims": []},
            required_parameter_ids={"p1"},
            uncertainty_by_parameter={},
            errors=errors4,
        )
        self.assertEqual(trust4, {"A": 0, "B": 0, "C": 0, "D": 0})
        self.assertEqual(total4, 1)
        self.assertEqual(missing4, 0)
        self.assertEqual(ratio4, 0.0)
        self.assertTrue(any("parameter_claims must be a non-empty array" in item for item in errors4))

        # Cover uncertainty empty-entry branch.
        errors5: list[str] = []
        out5 = evidence_validate._validate_uncertainty_model({"entries": []}, errors5)  # pylint: disable=protected-access
        self.assertEqual({}, out5)
        self.assertTrue(any("must be a non-empty array" in item for item in errors5))

    def test_schema_rule_branches_for_missing_parts(self) -> None:
        errors: list[str] = []
        evidence_validate._validate_evidence_schema_document(  # pylint: disable=protected-access
            {
                "type": "array",
                "required": [],
                "$defs": {
                    "EvidenceSource": {"required": []},
                    "ParameterClaim": {"required": [], "allOf": []},
                },
            },
            errors,
        )
        self.assertTrue(any("root type must be object" in item for item in errors))
        self.assertTrue(any("required list missing" in item for item in errors))
        self.assertTrue(any("EvidenceSource missing required fields" in item for item in errors))
        self.assertTrue(any("ParameterClaim missing required fields" in item for item in errors))
        self.assertTrue(any("mode/trust rules in allOf" in item for item in errors))

        errors2: list[str] = []
        evidence_validate._validate_evidence_schema_document(  # pylint: disable=protected-access
            {"type": "object", "required": ["schema_version", "evidence_sources", "parameter_claims"], "$defs": {}},
            errors2,
        )
        self.assertTrue(any("missing $defs.EvidenceSource" in item for item in errors2))
        self.assertTrue(any("missing $defs.ParameterClaim" in item for item in errors2))

    def test_git_helpers_and_changed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            _copy_contract_files(repo)
            head = _init_git_repo(repo)

            changed_clean = evidence_validate._changed_paths(repo, head, head)  # pylint: disable=protected-access
            self.assertEqual(set(), changed_clean)

            registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["parameter_claims"][0]["justification"] = "helper branch justification update"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
            changed_dirty = evidence_validate._changed_paths(repo, None, None)  # pylint: disable=protected-access
            self.assertIn("mission/EVIDENCE_REGISTRY_v1.json", changed_dirty)

            at_head = evidence_validate._file_at_ref(repo, head, Path("mission/EVIDENCE_REGISTRY_v1.json"))  # pylint: disable=protected-access
            self.assertIsInstance(at_head, dict)
            missing = evidence_validate._file_at_ref(repo, head, Path("mission/DOES_NOT_EXIST.json"))  # pylint: disable=protected-access
            self.assertIsNone(missing)

            notes: list[str] = []
            errors: list[str] = []
            # registry changed + changelog unchanged should trigger error path
            triggered = evidence_validate._enforce_drift_guard(  # pylint: disable=protected-access
                repo_root=repo,
                registry_path=Path("mission/EVIDENCE_REGISTRY_v1.json"),
                changelog_path=Path("engineering/CHANGELOG.md"),
                current_registry=registry,
                base=None,
                head=None,
                errors=errors,
                notes=notes,
            )
            self.assertTrue(triggered)
            self.assertTrue(errors)

            # Base branch path + no previous registry path.
            notes2: list[str] = []
            errors2: list[str] = []
            old_registry = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            old_registry.unlink()
            missing_prev = evidence_validate._enforce_drift_guard(  # pylint: disable=protected-access
                repo_root=repo,
                registry_path=Path("mission/EVIDENCE_REGISTRY_v1.json"),
                changelog_path=Path("engineering/CHANGELOG.md"),
                current_registry={},
                base=head,
                head=head,
                errors=errors2,
                notes=notes2,
            )
            self.assertFalse(missing_prev)

    def test_drift_guard_trigger_and_no_trigger_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            _copy_contract_files(repo)
            _init_git_repo(repo)

            registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["parameter_claims"][0]["justification"] = "new deterministic rationale"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

            changelog_path = repo / "engineering" / "CHANGELOG.md"
            changelog_path.write_text(changelog_path.read_text(encoding="utf-8") + "entry\n", encoding="utf-8")

            notes: list[str] = []
            errors: list[str] = []
            triggered = evidence_validate._enforce_drift_guard(  # pylint: disable=protected-access
                repo_root=repo,
                registry_path=Path("mission/EVIDENCE_REGISTRY_v1.json"),
                changelog_path=Path("engineering/CHANGELOG.md"),
                current_registry=registry,
                base=None,
                head=None,
                errors=errors,
                notes=notes,
            )
            self.assertTrue(triggered)
            self.assertEqual([], errors)
            self.assertTrue(any("changelog updated" in item for item in notes))

            # Force "registry changed without claim-level drift" branch:
            # reuse previous registry content as current input.
            previous = evidence_validate._file_at_ref(repo, "HEAD", Path("mission/EVIDENCE_REGISTRY_v1.json"))  # pylint: disable=protected-access
            notes2: list[str] = []
            errors2: list[str] = []
            _ = evidence_validate._enforce_drift_guard(  # pylint: disable=protected-access
                repo_root=repo,
                registry_path=Path("mission/EVIDENCE_REGISTRY_v1.json"),
                changelog_path=Path("engineering/CHANGELOG.md"),
                current_registry=previous if previous is not None else {},
                base=None,
                head=None,
                errors=errors2,
                notes=notes2,
            )
            self.assertTrue(any("without claim-level drift" in item for item in notes2))

    def test_error_branches_for_uncertainty_and_registry(self) -> None:
        # Uncertainty branches: non-dict entry + invalid fields.
        errors_unc: list[str] = []
        evidence_validate._validate_uncertainty_model(  # pylint: disable=protected-access
            {"entries": [123, {"parameter_id": "p.bad", "distribution": "bad", "parameters": {}, "bounds": "oops", "units": ""}]},
            errors_unc,
        )
        self.assertTrue(any("must be an object" in item for item in errors_unc))
        self.assertTrue(any("distribution 'bad' is invalid" in item for item in errors_unc))
        self.assertTrue(any("parameters must be non-empty object" in item for item in errors_unc))
        self.assertTrue(any("bounds must be object" in item for item in errors_unc))
        self.assertTrue(any("units must be non-empty string" in item for item in errors_unc))

        # Registry branches: malformed sources and claims.
        errors_reg: list[str] = []
        trust, total, missing, ratio = evidence_validate._validate_registry(  # pylint: disable=protected-access
            registry={
                "schema_version": "evidence_registry.v1",
                "evidence_sources": [
                    7,
                    {},
                    {"id": "SRC-X", "type": "paper", "citation": "ok", "url": None, "claim_scope": "ok", "notes": "ok"},
                    {"id": "SRC-X", "type": "paper", "citation": "ok", "url": None, "claim_scope": "ok", "notes": "ok"},
                ],
                "parameter_claims": [
                    1,
                    {
                        "parameter_id": "dup",
                        "value_mode": "bad",
                        "units": "",
                        "mode": "bad",
                        "evidence_source_ids": ["", "SRC-MISSING"],
                        "trust_grade": "Z",
                        "justification": "",
                        "last_reviewed_commit": "",
                    },
                    {
                        "parameter_id": "dup",
                        "value_mode": "distribution",
                        "units": "u",
                        "mode": "realistic",
                        "evidence_source_ids": [],
                        "trust_grade": "A",
                        "justification": "ok",
                        "last_reviewed_commit": "abcdef0",
                    },
                    {
                        "parameter_id": "dist-missing",
                        "value_mode": "distribution",
                        "units": "u",
                        "mode": "realistic",
                        "evidence_source_ids": ["SRC-X"],
                        "trust_grade": "A",
                        "justification": "ok",
                        "last_reviewed_commit": "abcdef0",
                    },
                    {
                        "parameter_id": "dist-nobounds",
                        "value_mode": "distribution",
                        "units": "u",
                        "mode": "realistic",
                        "evidence_source_ids": ["SRC-X"],
                        "trust_grade": "A",
                        "justification": "ok",
                        "last_reviewed_commit": "abcdef0",
                    },
                    {
                        "parameter_id": "dist-badbounds",
                        "value_mode": "distribution",
                        "units": "u",
                        "mode": "realistic",
                        "evidence_source_ids": ["SRC-X"],
                        "trust_grade": "A",
                        "justification": "ok",
                        "last_reviewed_commit": "abcdef0",
                    },
                ],
            },
            required_parameter_ids={"dup", "missing-required"},
            uncertainty_by_parameter={
                "dup": {"bounds": {"min": 0, "max": 1}},
                "dist-nobounds": {"bounds": None},
                "dist-badbounds": {"bounds": {"min": 5, "max": 5}},
            },
            errors=errors_reg,
        )
        self.assertEqual(total, 2)
        self.assertEqual(missing, 1)
        self.assertLess(ratio, 1.0)
        self.assertEqual(set(trust.keys()), {"A", "B", "C", "D"})
        self.assertTrue(any("must be object" in item for item in errors_reg))
        self.assertTrue(any("is duplicated" in item for item in errors_reg))
        self.assertTrue(any("value_mode 'bad' is invalid" in item for item in errors_reg))
        self.assertTrue(any("distribution claim requires uncertainty entry" in item for item in errors_reg))
        self.assertTrue(any("uncertainty bounds missing" in item for item in errors_reg))
        self.assertTrue(any("uncertainty bounds invalid" in item for item in errors_reg))

        # _trust_and_source_map branch where source IDs are not list.
        mapped = evidence_validate._trust_and_source_map(  # pylint: disable=protected-access
            {"parameter_claims": [{"parameter_id": "x", "trust_grade": "A", "evidence_source_ids": "bad"}]}
        )
        self.assertEqual(mapped["x"], ("A", tuple()))

    def test_drift_guard_base_mode_with_missing_previous_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "mission").mkdir(parents=True, exist_ok=True)
            (repo / "engineering").mkdir(parents=True, exist_ok=True)
            (repo / "engineering" / "CHANGELOG.md").write_text("initial\n", encoding="utf-8")
            _run(["git", "init"], cwd=repo)
            _run(["git", "config", "user.email", "tests@example.com"], cwd=repo)
            _run(["git", "config", "user.name", "Evidence Tests"], cwd=repo)
            _run(["git", "add", "."], cwd=repo)
            _run(["git", "commit", "-m", "base"], cwd=repo)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

            registry = {"schema_version": "evidence_registry.v1", "evidence_sources": [], "parameter_claims": []}
            (repo / "mission" / "EVIDENCE_REGISTRY_v1.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
            _run(["git", "add", "."], cwd=repo)
            _run(["git", "commit", "-m", "add-registry"], cwd=repo)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

            errors: list[str] = []
            notes: list[str] = []
            triggered = evidence_validate._enforce_drift_guard(  # pylint: disable=protected-access
                repo_root=repo,
                registry_path=Path("mission/EVIDENCE_REGISTRY_v1.json"),
                changelog_path=Path("engineering/CHANGELOG.md"),
                current_registry=registry,
                base=base,
                head=head,
                errors=errors,
                notes=notes,
            )
            self.assertTrue(triggered)
            self.assertTrue(any("no previous registry found" in item for item in notes))

    def test_main_entrypoint_and_internal_error(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "validator-output.json"
            with mock.patch.object(
                sys,
                "argv",
                [
                    "evidence_validate.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--strict",
                    "--format",
                    "json",
                    "--base",
                    head,
                    "--head",
                    head,
                    "--output",
                    str(out_path),
                ],
            ):
                code = evidence_validate.main()
            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())

        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_root = Path(tmp_dir)
            out_path = bad_root / "out.log"
            with mock.patch.object(
                sys,
                "argv",
                ["evidence_validate.py", "--repo-root", str(bad_root), "--strict", "--output", str(out_path)],
            ):
                code = evidence_validate.main()
            self.assertEqual(code, evidence_validate.EXIT_INTERNAL)
            self.assertTrue(out_path.exists())

        # strict=false with violations should return pass exit code branch.
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            _copy_contract_files(repo)
            _init_git_repo(repo)
            registry_path = repo / "mission" / "EVIDENCE_REGISTRY_v1.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["parameter_claims"][0]["mode"] = "realistic"
            registry["parameter_claims"][0]["trust_grade"] = "D"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
            out_path = repo / "out.txt"
            with mock.patch.object(
                sys,
                "argv",
                [
                    "evidence_validate.py",
                    "--repo-root",
                    str(repo),
                    "--output",
                    str(out_path),
                ],
            ):
                code = evidence_validate.main()
            self.assertEqual(code, evidence_validate.EXIT_PASS)
            self.assertTrue(out_path.exists())

    def test_run_as_main_covers_module_exit_path(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        with mock.patch.object(
            sys,
            "argv",
            [
                str(VALIDATOR),
                "--repo-root",
                str(REPO_ROOT),
                "--strict",
                "--base",
                head,
                "--head",
                head,
            ],
        ):
            with self.assertRaises(SystemExit) as exc:
                runpy.run_path(str(VALIDATOR), run_name="__main__")
        self.assertEqual(exc.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
