import unittest
import subprocess
import tempfile
from pathlib import Path
from deploy_scope import deployment_needed, changed_paths


class DeployScopeTests(unittest.TestCase):
    def test_ci_only_merge_never_publishes(self):
        self.assertFalse(deployment_needed(['AGENTS.md', '.github/ci-routing.json',
            '.github/ci-tools/deploy_scope.py', '.github/workflows/web-sim.yml']))

    def test_runtime_or_mixed_changes_keep_publication(self):
        for paths in [[], ['web/src/main.ts'], ['artifacts/research_signals.json'],
                      ['.github/workflows/web-sim.yml', 'web/package-lock.json']]:
            with self.subTest(paths=paths):
                self.assertTrue(deployment_needed(paths))

    def test_runtime_rename_into_ci_keeps_runtime_deletion_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q')
            git('config', 'user.name', 'CI fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'commit.gpgsign', 'false')
            (root/'web/public').mkdir(parents=True)
            (root/'web/public/asset.txt').write_text('unchanged runtime asset\n')
            git('add', '.')
            git('commit', '-qm', 'runtime fixture')
            base = git('rev-parse', 'HEAD')
            (root/'.github').mkdir()
            git('mv', 'web/public/asset.txt', '.github/asset.txt')
            git('commit', '-qm', 'move fixture')
            paths = changed_paths(base, git('rev-parse', 'HEAD'), root)
            self.assertEqual(set(paths), {'web/public/asset.txt', '.github/asset.txt'})
            self.assertTrue(deployment_needed(paths))

    def test_non_sha_comparisons_are_rejected(self):
        with self.assertRaises(ValueError):changed_paths('--output=unexpected', 'a'*40)
