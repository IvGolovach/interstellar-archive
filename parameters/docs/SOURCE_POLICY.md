# Source Policy

## Allowed source types
- `paper`
- `report`
- `dataset`
- `assumption`

## Minimal source record
Each source in `parameters/registry/evidence_sources.v1.json` must provide:
- `source_id`
- `type`
- `citation`
- `url` (nullable)
- `claim_scope`
- `notes`

## Binding rules
- Every parameter claim must reference one or more valid `source_id` values.
- `classification=assumed` parameters must reference at least one `assumption` source.
- Source IDs must resolve; dangling IDs fail CI.

## Non-goal
This layer validates source linkage and policy consistency. It does not auto-score scientific correctness of external literature.
