"""CI configuration changes must not publish the production site."""
import os
import subprocess


def deployment_needed(paths):
    # Empty/unknown comparisons retain the existing conservative deployment path.
    return not paths or any(path != 'AGENTS.md' and not path.startswith('.github/')
                            for path in paths)


if __name__ == '__main__':
    paths = subprocess.check_output(['git', 'diff', '--name-only',
        os.environ['BASE_SHA'], os.environ['HEAD_SHA'], '--'], text=True).splitlines()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('needed=' + str(deployment_needed(paths)).lower() + '\n')
