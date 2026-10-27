import unittest
from deploy_scope import deployment_needed


class DeployScopeTests(unittest.TestCase):
    def test_ci_only_merge_never_publishes(self):
        self.assertFalse(deployment_needed(['AGENTS.md', '.github/ci-routing.json',
            '.github/ci-tools/deploy_scope.py', '.github/workflows/web-sim.yml']))

    def test_runtime_or_mixed_changes_keep_publication(self):
        for paths in [[], ['web/src/main.ts'], ['artifacts/research_signals.json'],
                      ['.github/workflows/web-sim.yml', 'web/package-lock.json']]:
            with self.subTest(paths=paths):
                self.assertTrue(deployment_needed(paths))
