"""Governance enforcement package."""

from scripts.ci.governance.rules import GovernanceResult, run_governance_checks

__all__ = [
    "GovernanceResult",
    "run_governance_checks",
]

