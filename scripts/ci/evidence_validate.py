#!/usr/bin/env python3
"""Validate mission evidence contract and enforce evidence governance rules."""

from __future__ import annotations

try:
    from ._bootstrap import bootstrap_repo_root
except ImportError:
    from _bootstrap import bootstrap_repo_root


bootstrap_repo_root(__file__, levels=2)

from mission.evidence_validation import (  # noqa: E402
    DEFAULT_CHANGELOG,
    DEFAULT_EVIDENCE_REGISTRY,
    DEFAULT_EVIDENCE_SCHEMA,
    DEFAULT_MISSION_SCHEMA,
    DEFAULT_UNCERTAINTY_MODEL,
    EXIT_INTERNAL,
    EXIT_PASS,
    EXIT_VIOLATION,
    EvidenceValidationError,
    ValidationResult,
    main,
    run_validation,
)


if __name__ == "__main__":
    raise SystemExit(main())
