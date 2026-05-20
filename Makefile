.PHONY: repo-root-guard required-paths-validate golden-run benchmark-compare benchmark-drift-guard mission-baseline citation-validate model-version-validate version-contract-validate research-signals research-signals-validate evidence evidence-validate evidence-coverage evidence-status evidence-sync remote-proof audit test governance governance-coverage param-scan param-registry-validate param-evidence-validate param-drilldown-artifacts failure-surface-artifacts failure-surface-validate objective-artifacts objective-validate optimization-frontier-artifacts optimization-frontier-validate risk-envelope-validate artifact-determinism-validate param-domain-guard param-sensitivity defensibility-validate optimization-guard optimize optimize-verify optimization-coverage mission-dag-validate mission-dag-deps mission-dag-run mission-dag-coverage param-audit check

repo-root-guard:
	python3 scripts/ci/repo_root_guard.py --strict

required-paths-validate:
	python3 scripts/ci/required_paths_validate.py --strict

golden-run:
	python3 scripts/run_golden.py

benchmark-compare:
	python3 scripts/benchmark_compare.py

benchmark-drift-guard:
	python3 scripts/benchmark_drift_guard.py

mission-baseline:
	python3 scripts/mission_baseline_check.py --mode dual --verify-deterministic

citation-validate:
	python3 scripts/ci/validate_citation_cff.py

model-version-validate:
	python3 scripts/ci/validate_model_version.py

version-contract-validate:
	python3 scripts/ci/version_contract_validate.py --strict

evidence-validate:
	python3 scripts/ci/evidence_validate.py --strict

evidence-coverage:
	python3 scripts/ci/evidence_coverage.py --min 95

evidence-status:
	python3 scripts/build_evidence_status.py

research-signals: param-domain-guard
	python3 scripts/build_research_signals.py --no-require-tag

research-signals-validate:
	python3 scripts/ci/validate_research_signals.py --strict --no-require-tag

remote-proof:
	if [ -n "$(REMOTE_PROOF_DIR)" ]; then \
		python3 scripts/ci/remote_proof_aggregate.py --repo-root . --proof-dir "$(REMOTE_PROOF_DIR)"; \
	else \
		python3 scripts/ci/remote_proof_aggregate.py --repo-root .; \
	fi

param-scan:
	python3 scripts/ci/parameter_literal_scan.py --strict --format text

param-registry-validate:
	python3 scripts/ci/parameter_registry_validate.py --strict

param-evidence-validate:
	python3 scripts/ci/parameter_evidence_validate.py --strict

evidence-sync:
	python3 scripts/ci/evidence_sync_validate.py --strict

param-drilldown-artifacts:
	python3 scripts/build_parameter_drilldown_artifacts.py

failure-surface-artifacts:
	python3 scripts/build_failure_surface_artifacts.py

failure-surface-validate:
	python3 scripts/ci/failure_surface_validate.py --strict

objective-artifacts:
	python3 scripts/build_objective_artifacts.py

objective-validate:
	python3 scripts/ci/objective_contract_validate.py --strict

optimization-frontier-artifacts:
	python3 scripts/build_optimization_frontier.py

optimization-frontier-validate:
	python3 scripts/ci/optimization_frontier_validate.py --strict

risk-envelope-validate:
	python3 scripts/ci/risk_envelope_validate.py --strict

artifact-determinism-validate:
	python3 scripts/ci/artifact_determinism_validate.py --strict

param-domain-guard:
	python3 scripts/ci/parameter_domain_guard.py --strict --format json

param-sensitivity:
	python3 scripts/ci/parameter_sensitivity_report.py --mode realistic --baseline mission/BASELINE_SCENARIO_v1.json

defensibility-validate:
	python3 scripts/ci/defensibility_validate.py --strict

optimization-guard:
	python3 scripts/optimization_guard.py --strict

optimize:
	python3 scripts/run_optimization.py --mode realistic --samples 96 --seed 42

optimize-verify:
	python3 scripts/run_optimization.py --mode realistic --samples 96 --seed 42 --verify-deterministic

optimization-coverage:
	python3 scripts/ci/optimization_coverage.py --min 90

mission-dag-validate:
	python3 scripts/ci/mission_dag_validate.py --strict

mission-dag-deps:
	python3 scripts/ci/dag_dependency_graph.py --strict

mission-dag-run:
	python3 scripts/run_mission_dag.py --scenario mission/dag/scenarios/mission_dag_baseline.v1.json --mode dual --seed 1 --verify-deterministic --run-id check-mission-dag-v1
	python3 scripts/ci/mission_dag_validate.py --strict --artifacts-dir ops/reports/mission-dag-v1/check-mission-dag-v1

mission-dag-coverage:
	python3 scripts/ci/mission_dag_coverage.py --min 90

param-audit: param-scan param-registry-validate param-evidence-validate evidence-sync param-drilldown-artifacts failure-surface-artifacts failure-surface-validate objective-artifacts objective-validate optimization-frontier-artifacts optimization-frontier-validate risk-envelope-validate artifact-determinism-validate param-domain-guard param-sensitivity defensibility-validate optimization-guard

evidence:
	python3 scripts/build_evidence_artifacts.py

audit:
	python3 scripts/audit_claim_chain.py

test:
	python3 -m unittest discover -s tests -p "test_*.py"

governance:
	if [ -n "$(BASE_SHA)" ] && [ -n "$(HEAD_SHA)" ]; then \
		BASE_SHA="$(BASE_SHA)"; \
		HEAD_SHA="$(HEAD_SHA)"; \
	else \
		if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then \
			if git rev-parse --verify origin/main >/dev/null 2>&1; then \
				BASE_SHA=$$(git merge-base origin/main HEAD); \
			else \
				BASE_SHA=$$(git rev-parse HEAD~1); \
			fi; \
		else \
			BASE_SHA=$$(git rev-parse HEAD); \
		fi; \
		HEAD_SHA=$$(git rev-parse HEAD); \
	fi; \
	python3 scripts/ci/governance_check.py --base $$BASE_SHA --head $$HEAD_SHA --repo-root .

governance-coverage:
	python3 scripts/ci/governance_coverage.py --min 95

check:
	BASE_SHA="$(BASE_SHA)" HEAD_SHA="$(HEAD_SHA)" REMOTE_PROOF_DIR="$(REMOTE_PROOF_DIR)" python3 scripts/ci/check_suite.py
