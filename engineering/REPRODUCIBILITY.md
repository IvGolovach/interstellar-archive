# Reproducibility Protocol

## 1. How to clone and build

```bash
git clone https://github.com/IvGolovach/interstellar-archive.git
cd interstellar-archive
```

## 2. Deterministic setup instructions

The governance/evidence pipeline uses Python standard library only.

Required runtime:
- Python 3.11.x
- POSIX shell (`bash`)
- `git`

Set locale/timezone explicitly for stable metadata rendering:

```bash
export LC_ALL=C
export TZ=UTC
```

## 3. Exact dependency versions

No third-party Python dependencies are required for the governance proof pipeline.

Reference interpreter:
- Python 3.11

Optional exploratory notebooks (`appendix/models/*.ipynb`) require separate scientific packages and are not part of the deterministic governance pipeline.

## 4. How to reproduce a full run

```bash
scripts/run_evidence_checks.sh
```

Equivalent:

```bash
make check
```

## 5. Expected outputs

After a successful run, the following outputs must exist:

- `artifacts/claim_values.json`
- `artifacts/claims_table.csv`
- `artifacts/traceability_matrix.csv`
- `artifacts/claims_report.md`
- `artifacts/evidence-pack-v1/metadata.json`
- `artifacts/evidence-pack-v1/input_parameters.json`
- `artifacts/evidence-pack-v1/checksums.sha256`

## 6. How to verify outputs integrity

1. Recompute hashes:

```bash
shasum -a 256 -c artifacts/evidence-pack-v1/checksums.sha256
```

2. Verify generation commit linkage:

```bash
python3 - <<'PY'
import json
from pathlib import Path
meta = json.loads(Path("artifacts/evidence-pack-v1/metadata.json").read_text())
print(meta["generation_commit_sha"])
PY
```

3. Confirm CI-equivalent checks:

```bash
python3 scripts/audit_claim_chain.py
python3 -m unittest discover -s tests -p "test_*.py"
if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
  BASE_SHA=$(git rev-parse HEAD~1)
else
  BASE_SHA=$(git rev-parse HEAD)
fi
HEAD_SHA=$(git rev-parse HEAD)
python3 scripts/ci/governance_check.py --base "$BASE_SHA" --head "$HEAD_SHA" --repo-root .
python3 scripts/ci/governance_coverage.py --min 95
```

Deterministic controls:
- deterministic formulas (no stochastic branch in governance scripts),
- fixed reference constants,
- no randomized seeds used in governance pipeline.
- governance enforcement uses deterministic git range inputs (`--base`, `--head`) and locale-locked subprocess execution (`LANG=C`, `LC_ALL=C`).

Exploratory simulation note:
- `appendix/models/monte_carlo.ipynb` uses `numpy.random.default_rng(42)` as the notebook seed.

Expected checksum manifest for current baseline:

```text
0bed4fac5e0cfe6328dc9ce5ea70f5851e3f27376f094c6c3e8d2944778651f7  artifacts/claim_values.json
4937f3d135a1b2a57b26af24fca7646dd6d39ac6a9558ca26444e3c5f6c280b2  artifacts/claims_report.md
f1b853c2152bba95acb512a28f76eb9088c0dddb9532aa17c769f05edb6c93bd  artifacts/claims_table.csv
6d513f40a331c4e016c1f9892448945d9d19bce22dcb8128e3112202d5d0d074  artifacts/traceability_matrix.csv
```

## 7. Proof artifact storage policy

Governance and CI proof logs are intentionally not stored as tracked repository content under `ops/reports/`.

Policy:
- canonical proofs live in GitHub Actions run artifacts and run URLs;
- local ad-hoc proofs may exist only in ignored paths (for example `ops/reports/` while debugging, or an external archive);
- repository keeps stable governance docs and compact proof pointers, not raw transient logs.
