from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest
import shutil

from scripts import build_research_signals
from scripts.ci import validate_research_signals


REPO_ROOT = Path(__file__).resolve().parents[1]


class ResearchSignalsTests(unittest.TestCase):
    def test_build_payload_matches_required_contract_fields(self) -> None:
        payload = build_research_signals.build_research_signals_payload(REPO_ROOT, require_tag=False)
        self.assertEqual("v1", payload["engine_version"])
        self.assertEqual("sim_schema.v2", payload["schema_version"])
        self.assertTrue(payload["golden_checksum"].startswith("bda117f"))
        self.assertIn(payload["ci_status"], {"passing", "failing"})
        self.assertIsInstance(payload["realistic_mode_verified"], bool)
        self.assertIsInstance(payload["speculative_mode_enabled"], bool)

    def test_repo_research_signals_validates_strict(self) -> None:
        errors = validate_research_signals._validate_shape(  # type: ignore[attr-defined]
            validate_research_signals._read_json(REPO_ROOT / "artifacts" / "research_signals.json")  # type: ignore[attr-defined]
        )
        self.assertEqual([], errors)

    def test_detects_checksum_short_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            signals = REPO_ROOT / "artifacts" / "research_signals.json"
            payload = json.loads(signals.read_text(encoding="utf-8"))
            payload["golden_checksum_short"] = "deadbee..."
            temp_file = Path(tmp_dir) / "research_signals.json"
            temp_file.write_text(json.dumps(payload), encoding="utf-8")
            loaded = validate_research_signals._read_json(temp_file)  # type: ignore[attr-defined]
            errors = validate_research_signals._validate_shape(loaded)  # type: ignore[attr-defined]
            self.assertTrue(any("golden_checksum_short" in err for err in errors))

    def test_build_payload_without_prebuilt_domain_status_file(self) -> None:
        domain_status = REPO_ROOT / "artifacts" / "domain_mode_status.json"
        backup = None
        if domain_status.exists():
            backup = domain_status.with_suffix(".json.bak-test")
            shutil.move(str(domain_status), str(backup))
        try:
            payload = build_research_signals.build_research_signals_payload(REPO_ROOT, require_tag=False)
            self.assertIn(payload["ci_status"], {"passing", "failing"})
            self.assertIsInstance(payload["realistic_mode_verified"], bool)
            self.assertIsInstance(payload["speculative_mode_enabled"], bool)
        finally:
            if backup and backup.exists():
                shutil.move(str(backup), str(domain_status))


if __name__ == "__main__":
    unittest.main()
