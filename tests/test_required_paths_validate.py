from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from scripts.ci import required_paths_validate


class RequiredPathsValidateTests(unittest.TestCase):
    def test_repo_manifest_validates(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest = required_paths_validate.load_manifest(repo_root / "docs" / "required_paths.v1.json")
        errors = required_paths_validate._validate_manifest_shape(  # type: ignore[attr-defined]
            manifest,
            repo_root / "docs" / "required_paths.v1.json",
        )
        errors.extend(required_paths_validate.validate_required_paths(repo_root, manifest))
        self.assertEqual([], errors)

    def test_detects_missing_required_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            docs_dir = repo_root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = docs_dir / "required_paths.v1.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "required_paths.v1",
                        "groups": [
                            {
                                "id": "sample",
                                "description": "sample contract",
                                "paths": ["docs/present.md", "docs/missing.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (docs_dir / "present.md").write_text("ok\n", encoding="utf-8")

            manifest = required_paths_validate.load_manifest(manifest_path)
            errors = required_paths_validate.validate_required_paths(repo_root, manifest)

        self.assertTrue(any("missing file: docs/missing.md" in error for error in errors))

    def test_rejects_duplicate_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "required_paths.v1.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "required_paths.v1",
                        "groups": [
                            {
                                "id": "sample",
                                "description": "sample contract",
                                "paths": ["README.md", "README.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            manifest = required_paths_validate.load_manifest(manifest_path)
            errors = required_paths_validate._validate_manifest_shape(  # type: ignore[attr-defined]
                manifest,
                manifest_path,
            )

        self.assertTrue(any("duplicate path" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
