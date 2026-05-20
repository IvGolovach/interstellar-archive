#!/usr/bin/env python3
"""Compare current golden-run metrics against baseline registry."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    from .script_io import load_json, render_json as render_json_output, write_text
except ImportError:
    from script_io import load_json, render_json as render_json_output, write_text

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
BASELINE_PATH = BENCHMARKS_DIR / "baseline_registry.json"
DEFINITIONS_PATH = BENCHMARKS_DIR / "benchmark_definitions.json"
CURRENT_METRICS_PATH = REPO_ROOT / "artifacts" / "evidence-pack-v1" / "output_metrics.json"


class BenchmarkCompareError(RuntimeError):
    """Raised when benchmark inputs are invalid."""


@dataclass(frozen=True)
class MetricResult:
    metric_name: str
    status: str
    baseline: float
    current: float
    delta: float
    units: str
    reason: str


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
    except FileNotFoundError as exc:
        raise BenchmarkCompareError(f"missing file: {path.relative_to(REPO_ROOT)}") from exc
    except ValueError as exc:
        raise BenchmarkCompareError(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkCompareError(f"{path.relative_to(REPO_ROOT)} must contain a top-level JSON object")
    return payload


def _get_latest_baseline(entries: List[Dict[str, Any]], metric_name: str) -> Dict[str, Any]:
    metric_entries = [entry for entry in entries if entry.get("metric_name") == metric_name]
    if not metric_entries:
        raise BenchmarkCompareError(f"baseline missing for metric '{metric_name}'")
    metric_entries.sort(key=lambda item: (str(item.get("date", "")), str(item.get("commit_sha", ""))))
    return metric_entries[-1]


def _threshold_ok(current: float, threshold: Dict[str, Any]) -> bool:
    threshold_type = str(threshold.get("type", "")).lower()
    value = float(threshold.get("value", 0.0))

    if threshold_type == "floor":
        return current >= value
    if threshold_type == "ceiling":
        return current <= value
    raise BenchmarkCompareError(f"unsupported threshold type: {threshold_type}")


def compare_metrics() -> List[MetricResult]:
    definitions = _read_json(DEFINITIONS_PATH)
    baseline_registry = _read_json(BASELINE_PATH)
    current_metrics = _read_json(CURRENT_METRICS_PATH)

    metrics = definitions.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise BenchmarkCompareError("benchmark_definitions.json must contain non-empty 'metrics' list")

    baseline_entries = baseline_registry.get("entries")
    if not isinstance(baseline_entries, list) or not baseline_entries:
        raise BenchmarkCompareError("baseline_registry.json must contain non-empty 'entries' list")

    results: List[MetricResult] = []
    for metric in metrics:
        metric_name = str(metric.get("metric_name", "")).strip()
        if not metric_name:
            raise BenchmarkCompareError("metric definition missing metric_name")

        if metric_name not in current_metrics:
            raise BenchmarkCompareError(f"current output metrics missing '{metric_name}'")

        baseline = _get_latest_baseline(baseline_entries, metric_name)
        baseline_value = float(baseline["metric_value"])
        current_value = float(current_metrics[metric_name])
        delta = current_value - baseline_value

        units = str(metric.get("units", "unitless"))
        acceptable_variance = float(metric.get("acceptable_variance", 0.0))
        higher_is_better = bool(metric.get("higher_is_better", True))
        threshold = metric.get("regression_threshold")
        if not isinstance(threshold, dict):
            raise BenchmarkCompareError(f"metric '{metric_name}' missing regression_threshold object")

        if higher_is_better:
            baseline_ok = current_value >= (baseline_value - acceptable_variance)
            baseline_reason = "current >= baseline - variance"
        else:
            baseline_ok = current_value <= (baseline_value + acceptable_variance)
            baseline_reason = "current <= baseline + variance"

        threshold_ok = _threshold_ok(current_value, threshold)
        threshold_reason = f"threshold {threshold.get('type')}={threshold.get('value')}"

        status = "PASS" if (baseline_ok and threshold_ok) else "REGRESSION"
        reason = f"{baseline_reason}; {threshold_reason}"
        results.append(
            MetricResult(
                metric_name=metric_name,
                status=status,
                baseline=baseline_value,
                current=current_value,
                delta=delta,
                units=units,
                reason=reason,
            )
        )

    return results


def render_text(results: List[MetricResult]) -> str:
    lines = ["Benchmark compare result"]
    regressions = 0
    for result in results:
        if result.status != "PASS":
            regressions += 1
        lines.append(
            (
                f"- {result.metric_name}: {result.status} "
                f"(baseline={result.baseline:.9g}, current={result.current:.9g}, "
                f"delta={result.delta:+.9g}, units={result.units})"
            )
        )
        lines.append(f"  reason: {result.reason}")

    lines.append(f"Summary: total={len(results)} regressions={regressions}")
    return "\n".join(lines)


def _build_payload(results: List[MetricResult]) -> Dict[str, Any]:
    return {
        "status": "PASS" if all(result.status == "PASS" for result in results) else "FAIL",
        "results": [
            {
                "metric_name": result.metric_name,
                "status": result.status,
                "baseline": result.baseline,
                "current": result.current,
                "delta": result.delta,
                "units": result.units,
                "reason": result.reason,
            }
            for result in results
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", help="Optional output file path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        results = compare_metrics()
    except BenchmarkCompareError as exc:
        print(f"Benchmark compare FAIL: {exc}")
        return 3

    payload = _build_payload(results)
    rendered = (
        render_json_output(payload, indent=2, sort_keys=False)
        if args.format == "json"
        else render_text(results)
    )
    print(rendered)
    if args.output:
        write_text(Path(args.output), rendered)

    return 0 if all(result.status == "PASS" for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
