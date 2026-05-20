from __future__ import annotations

import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _bootstrap import bootstrap_repo_root, ensure_repo_on_path, resolve_repo_root


class ScriptBootstrapTests(unittest.TestCase):
    def test_resolve_repo_root_supports_top_level_and_ci_scripts(self) -> None:
        self.assertEqual(
            REPO_ROOT,
            resolve_repo_root(REPO_ROOT / "scripts" / "mission_baseline_check.py", levels=1),
        )
        self.assertEqual(
            REPO_ROOT,
            resolve_repo_root(REPO_ROOT / "scripts" / "ci" / "check_suite.py", levels=2),
        )

    def test_ensure_repo_on_path_is_idempotent(self) -> None:
        original = list(sys.path)
        try:
            while str(REPO_ROOT) in sys.path:
                sys.path.remove(str(REPO_ROOT))

            ensure_repo_on_path(REPO_ROOT)
            ensure_repo_on_path(REPO_ROOT)

            self.assertEqual(1, sys.path.count(str(REPO_ROOT)))
            self.assertEqual(str(REPO_ROOT), sys.path[0])
        finally:
            sys.path[:] = original

    def test_scripts_do_not_inline_repo_root_sys_path_bootstrap(self) -> None:
        excluded = {
            Path("scripts/_bootstrap.py"),
            Path("scripts/ci/_bootstrap.py"),
        }
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "scripts").rglob("*.py")):
            rel_path = path.relative_to(REPO_ROOT)
            if rel_path in excluded:
                continue
            text = path.read_text(encoding="utf-8")
            if "sys.path.insert(0, str(REPO_ROOT))" in text:
                offenders.append(str(rel_path))

        self.assertEqual([], offenders)

    def test_bootstrap_repo_root_can_skip_sys_path_mutation(self) -> None:
        original = list(sys.path)
        try:
            while str(REPO_ROOT) in sys.path:
                sys.path.remove(str(REPO_ROOT))

            repo_root = bootstrap_repo_root(
                REPO_ROOT / "scripts" / "ci" / "optimization_coverage.py",
                levels=2,
                add_to_sys_path=False,
            )

            self.assertEqual(REPO_ROOT, repo_root)
            self.assertNotIn(str(REPO_ROOT), sys.path)
        finally:
            sys.path[:] = original


if __name__ == "__main__":
    unittest.main()
