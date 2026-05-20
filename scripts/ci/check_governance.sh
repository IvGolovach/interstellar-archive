#!/usr/bin/env bash
set -euo pipefail

BASE_SHA="${BASE_SHA:-${1:-}}"
HEAD_SHA="${HEAD_SHA:-${2:-}}"
REPO_ROOT="${REPO_ROOT:-${3:-.}}"

if [[ -z "${HEAD_SHA}" ]]; then
  echo "HEAD_SHA is required"
  exit 3
fi

if [[ -z "${BASE_SHA}" || "${BASE_SHA}" == "0000000000000000000000000000000000000000" ]]; then
  BASE_SHA="$(git -C "${REPO_ROOT}" rev-parse "${HEAD_SHA}^" 2>/dev/null || true)"
fi

if [[ -z "${BASE_SHA}" ]]; then
  echo "Unable to resolve BASE_SHA"
  exit 3
fi

exec python3 scripts/ci/governance_check.py --base "${BASE_SHA}" --head "${HEAD_SHA}" --repo-root "${REPO_ROOT}"

