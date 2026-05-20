# Engineering Governance Policy

## Scope

This policy governs engineering changes in this repository with minimal process overhead.

## Mandatory Rules

1. No force-push on `main`.
2. No history rewrite on `main`.
3. Every non-trivial change requires a controlled entry in `engineering/CHANGELOG.md`.
4. Every architecture-level change requires an entry in `engineering/DECISIONS.md`.
5. All public artifacts must be reproducible via repository scripts.
6. No undocumented behavior changes: if behavior changes, documentation must be updated in the same change set.

## Documentation Update Contract

- Quantitative or core logic changes (`models/`, `scripts/`, equivalent core paths):
  update `engineering/CHANGELOG.md`.
- Architecture/governance contract changes (`engineering/ARCHITECTURE.md`, `engineering/GOVERNANCE.md`, `engineering/REPRODUCIBILITY.md`):
  update `engineering/DECISIONS.md`.

### Commit-SHA logging protocol

Because a commit cannot safely self-reference its own final SHA in file content, use this sequence for strict traceability:

1. Commit the substantive change.
2. Add `engineering/CHANGELOG.md` entry referencing that commit SHA.
3. Commit the changelog update.

CI validates that changelog references at least one SHA from the active change range.

## Governance Enforcement v2 (Python)

Primary enforcement tool:

- `scripts/ci/governance_check.py`

Policy source:

- `engineering/governance_policy.yaml`

### Proof storage policy

- `ops/reports/**` is local-only and ignored by git.
- Auditable proof for public review must be referenced through PR links and GitHub Actions run URLs.
- Tracked repository content should remain compact: governance contracts, reproducibility instructions, and closeout pointers only.

### How to run governance check locally

```bash
BASE_SHA=$(git rev-parse HEAD~1 2>/dev/null || git rev-parse HEAD)
HEAD_SHA=$(git rev-parse HEAD)
python3 scripts/ci/governance_check.py --base "$BASE_SHA" --head "$HEAD_SHA" --repo-root .
```

JSON output:

```bash
python3 scripts/ci/governance_check.py --base "$BASE_SHA" --head "$HEAD_SHA" --repo-root . --format json
```

### How to interpret failures

Text output reports:
1. Rule ID (`rule_id`).
2. Evidence (changed files, missing docs, parse errors, checksum mismatches).
3. Required fix action.

Exit codes:
1. `0` -> pass
2. `2` -> governance violation
3. `3` -> internal tool error

### How to add a new rule safely

1. Update policy schema/data in `engineering/governance_policy.yaml`.
2. Implement rule logic in `scripts/ci/governance/rules.py`.
3. Add parser/config helpers only if necessary.
4. Add unit tests (`tests/test_governance_check_unit.py`).
5. Add integration/edge scenarios where applicable.
6. Run:
   - `python3 scripts/ci/governance_check.py ...`
   - `python3 scripts/ci/governance_coverage.py --min 95`

## Future Contributors Policy

### How to submit PRs

1. Open a branch from `main`.
2. Implement changes with tests.
3. Run `make check` locally.
4. Update required governance docs.
5. Open PR with concise summary and rationale.

### Which documents to update

- `engineering/CHANGELOG.md` for non-trivial code or behavior changes.
- `engineering/DECISIONS.md` for architectural policy or system-contract changes.
- `engineering/ARCHITECTURE.md` when invariants/trust boundaries/failure modes change.
- `engineering/REPRODUCIBILITY.md` when build/run/verification steps change.

### What counts as a breaking change

A change is breaking if it modifies:
- claim semantics or interpretation contract,
- artifact formats or required output files,
- evidence chain contract (`claim -> assumption -> model -> artifact -> source`),
- public run commands in a non-backward-compatible way.
