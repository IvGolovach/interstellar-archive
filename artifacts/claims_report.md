# Evidence Report

This report is generated from deterministic models and structured claim metadata.

## Summary

- Claims covered: 9
- Numeric checks: 22
- Passed checks: 22
- Failed checks: 0

## Claim Snapshot

| Claim ID | Key Metrics |
| --- | --- |
| C-001 | `r_s_km`=29.5333938 |
| C-002 | `flux_0p10_au_mw_m2`=0.1361; `flux_0p05_au_mw_m2`=0.5444 |
| C-003 | `vinf_baseline_min_km_s`=23.1690476; `vinf_baseline_max_km_s`=33.7527715 |
| C-004 | `vinf_conditional_min_km_s`=35.2255736; `vinf_conditional_max_km_s`=45.3154825 |
| C-005 | `delta_v_1000_au_min_m_s`=0.233133122; `delta_v_1000_au_max_m_s`=0.456130021; `delta_v_100_au_min_m_s`=0.0233133122; `delta_v_100_au_max_m_s`=0.0456130021 |
| C-006 | `tof_baseline_min_myr`=13.7551834; `tof_baseline_max_myr`=20.3337493; `tof_conditional_min_myr`=10.3928052; `tof_conditional_max_myr`=13.3621781 |
| C-007 | `rtg_fraction_10y`=0.924006506; `rtg_fraction_50y`=0.673558227; `rtg_fraction_half_life`=0.5; `rtg_fraction_1000y`=0.000369405111 |
| C-008 |  |
| C-009 | `archive_cost_anchor_usd`=100000000; `flagship_cost_anchor_usd`=1e+09; `cost_anchor_ratio`=10 |

## Rebuild Commands

```bash
python3 scripts/build_evidence_artifacts.py
python3 scripts/audit_claim_chain.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Traceability

See `artifacts/traceability_matrix.csv` for claim -> assumption -> model -> artifact -> source linkage.
