#!/usr/bin/env bash
set -euo pipefail

exec python3 scripts/ci/check_suite.py "$@"
