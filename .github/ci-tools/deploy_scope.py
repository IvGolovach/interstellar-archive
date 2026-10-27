"""CI configuration changes must not publish the production site."""
import os
import re
import subprocess


def deployment_needed(paths):
    # Empty/unknown comparisons retain the existing conservative deployment path.
    return not paths or any(path != 'AGENTS.md' and not path.startswith('.github/')
                            for path in paths)


def changed_paths(base, head, cwd=None):
    if not all(re.fullmatch(r'[0-9a-f]{40}', ref) for ref in [base, head]):
        raise ValueError('Expected full GitHub commit SHAs')
    # A move into .github must still report the removed runtime source path.
    result = subprocess.check_output(['git', 'diff', '--no-renames', '--name-only', '-z',
        base, head, '--'], cwd=cwd, text=True)
    return [path for path in result.split('\0') if path]


if __name__ == '__main__':
    paths = changed_paths(os.environ['BASE_SHA'], os.environ['HEAD_SHA'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('needed=' + str(deployment_needed(paths)).lower() + '\n')
