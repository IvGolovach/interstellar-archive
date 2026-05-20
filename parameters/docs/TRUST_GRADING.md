# Trust Grading

## Grades
- `A`: direct high-confidence source with narrow uncertainty and stable provenance.
- `B`: source-backed value with moderate assumptions or aggregation.
- `C`: bounded estimate/assumption with explicit uncertainty and rationale.
- `D`: speculative-only value (non-physical exploration controls).

## Policy
- `realistic` mode: grades `A/B/C` only.
- `speculative` mode: `D` allowed.
- `D` in realistic mode is prohibited and fails CI.

## Upgrade path
To upgrade trust for a parameter:
1. Replace assumption-only source with paper/report/dataset source(s).
2. Narrow bounds in registry and uncertainty model if justified.
3. Update claim justification and `last_reviewed_commit`.
4. Re-run strict validators and sensitivity report.
