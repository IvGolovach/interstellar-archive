from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
import json
import hashlib

from models.evidence_io import REFS_BIB_PATH, load_assumptions, load_claims, load_sources, parse_bibliography_keys


REPO_ROOT = Path(__file__).resolve().parents[1]


class TraceabilityChainTests(unittest.TestCase):
    def test_all_links_resolve_in_registry(self) -> None:
        claims = load_claims()["claims"]
        assumptions = load_assumptions()
        sources = load_sources()

        for claim in claims:
            self.assertTrue(claim["assumption_ids"], msg=f"{claim['id']} missing assumptions")
            self.assertTrue(claim["source_ids"], msg=f"{claim['id']} missing sources")
            if claim["checks"]:
                self.assertNotEqual(
                    claim.get("verification_mode"),
                    "qualitative",
                    msg=f"{claim['id']} qualitative claim should not define numeric checks",
                )
            else:
                self.assertEqual(
                    claim.get("verification_mode"),
                    "qualitative",
                    msg=f"{claim['id']} missing checks without qualitative verification_mode",
                )

            for assumption_id in claim["assumption_ids"]:
                self.assertIn(assumption_id, assumptions, msg=f"{claim['id']} -> {assumption_id}")
            for source_id in claim["source_ids"]:
                self.assertIn(source_id, sources, msg=f"{claim['id']} -> {source_id}")

    def test_bibliography_keys_exist(self) -> None:
        bib_keys = parse_bibliography_keys(REFS_BIB_PATH.read_text(encoding="utf-8"))
        sources = load_sources()
        for source in sources.values():
            if source["kind"] == "bibliography":
                self.assertIn(source["cite_key"], bib_keys, msg=source["id"])

    def test_audit_script_passes(self) -> None:
        subprocess.run(
            ["python3", "scripts/run_golden.py"],
            cwd=REPO_ROOT,
            check=True,
        )
        result = subprocess.run(
            ["python3", "scripts/audit_claim_chain.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stdout + "\n" + result.stderr)

    def test_artifact_pack_checksums_match(self) -> None:
        subprocess.run(
            ["python3", "scripts/run_golden.py"],
            cwd=REPO_ROOT,
            check=True,
        )
        pack_dir = REPO_ROOT / "artifacts" / "evidence-pack-v1"
        metadata = json.loads((pack_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["generation_commit_sha"])

        checksums = (pack_dir / "checksums.sha256").read_text(encoding="utf-8").strip().splitlines()
        for line in checksums:
            digest, rel_path = line.split("  ", 1)
            target_path = REPO_ROOT / rel_path
            self.assertTrue(target_path.exists(), msg=rel_path)
            actual = hashlib.sha256(target_path.read_bytes()).hexdigest()
            self.assertEqual(digest, actual, msg=rel_path)


if __name__ == "__main__":
    unittest.main()
