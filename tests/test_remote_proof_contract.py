from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from scripts.ci import remote_proof_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
REMOTE_CI_VALIDATE = REPO_ROOT / "scripts" / "ci" / "remote_ci_web_validate.py"
REMOTE_BRANCH_VALIDATE = REPO_ROOT / "scripts" / "ci" / "remote_branch_web_validate.py"
REMOTE_AGGREGATE = REPO_ROOT / "scripts" / "ci" / "remote_proof_aggregate.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _origin_main_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=REPO_ROOT, text=True).strip()


def _ci_payload(commit_sha: str) -> dict[str, object]:
    return {
        "source": "github_web",
        "repository": "IvGolovach/interstellar-archive",
        "branch": "main",
        "commit_sha": commit_sha,
        "actions_run_url": "https://github.com/IvGolovach/interstellar-archive/actions/runs/99999999999",
        "run_status": "success",
        "required_contexts_verified": [
            "evidence",
            "governance",
            "verify-web-sim",
            "floating-point-stability",
        ],
        "collected_at_utc": "2026-02-18T00:00:00Z",
    }


def _branch_payload() -> dict[str, object]:
    return {
        "source": "github_web",
        "branch": "main",
        "require_pr": True,
        "allow_force_pushes": False,
        "required_status_checks": ["evidence", "governance"],
        "collected_at_utc": "2026-02-18T00:00:00Z",
    }


class RemoteProofContractTests(unittest.TestCase):
    def test_validate_ci_payload_passes(self) -> None:
        expected = _origin_main_sha()
        result = remote_proof_contract.validate_ci_payload(_ci_payload(expected), expected_origin_main_sha=expected)
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["commit_match"])

    def test_validate_ci_payload_fails_on_commit_mismatch(self) -> None:
        expected = _origin_main_sha()
        result = remote_proof_contract.validate_ci_payload(_ci_payload("deadbeef"), expected_origin_main_sha=expected)
        self.assertEqual("FAIL", result["status"])
        self.assertFalse(result["commit_match"])
        self.assertTrue(any("commit_sha mismatch" in err for err in result["errors"]))

    def test_validate_branch_payload_fails_on_force_push(self) -> None:
        payload = _branch_payload()
        payload["allow_force_pushes"] = True
        result = remote_proof_contract.validate_branch_payload(payload)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("allow_force_pushes must be false" in err for err in result["errors"]))

    def test_cli_validators_pass_with_valid_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            ci_file = root / "REMOTE_PROOF_CI_WEB.json"
            branch_file = root / "REMOTE_PROOF_BRANCH_PROTECTION_WEB.json"
            ci_file.write_text(json.dumps(_ci_payload(_origin_main_sha()), indent=2) + "\n", encoding="utf-8")
            branch_file.write_text(json.dumps(_branch_payload(), indent=2) + "\n", encoding="utf-8")

            ci_proc = _run(
                [
                    sys.executable,
                    str(REMOTE_CI_VALIDATE),
                    "--repo-root",
                    str(REPO_ROOT),
                    "--proof-file",
                    str(ci_file),
                ],
                cwd=REPO_ROOT,
            )
            self.assertEqual(0, ci_proc.returncode, ci_proc.stdout + ci_proc.stderr)
            self.assertIn("PASS", ci_proc.stdout)

            branch_proc = _run(
                [sys.executable, str(REMOTE_BRANCH_VALIDATE), "--proof-file", str(branch_file)],
                cwd=REPO_ROOT,
            )
            self.assertEqual(0, branch_proc.returncode, branch_proc.stdout + branch_proc.stderr)
            self.assertIn("PASS", branch_proc.stdout)

    def test_aggregate_generates_pass_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            proof_dir = Path(tmp_dir)
            ci_file = proof_dir / "REMOTE_PROOF_CI_WEB.json"
            branch_file = proof_dir / "REMOTE_PROOF_BRANCH_PROTECTION_WEB.json"
            ci_file.write_text(json.dumps(_ci_payload(_origin_main_sha()), indent=2) + "\n", encoding="utf-8")
            branch_file.write_text(json.dumps(_branch_payload(), indent=2) + "\n", encoding="utf-8")

            proc = _run(
                [
                    sys.executable,
                    str(REMOTE_AGGREGATE),
                    "--repo-root",
                    str(REPO_ROOT),
                    "--proof-dir",
                    str(proof_dir),
                ],
                cwd=REPO_ROOT,
            )
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            summary = json.loads((proof_dir / "REMOTE_PROOF_SUMMARY.json").read_text(encoding="utf-8"))
            self.assertEqual("PASS", summary["verdict"])
            self.assertTrue(summary["commit_match"])

    def test_aggregate_fails_when_proof_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            proof_dir = Path(tmp_dir)
            (proof_dir / "REMOTE_PROOF_CI_WEB.json").write_text(
                json.dumps(_ci_payload(_origin_main_sha()), indent=2) + "\n",
                encoding="utf-8",
            )
            proc = _run(
                [
                    sys.executable,
                    str(REMOTE_AGGREGATE),
                    "--repo-root",
                    str(REPO_ROOT),
                    "--proof-dir",
                    str(proof_dir),
                ],
                cwd=REPO_ROOT,
            )
            self.assertEqual(remote_proof_contract.EXIT_INTERNAL, proc.returncode)
            self.assertIn("missing proof file", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
