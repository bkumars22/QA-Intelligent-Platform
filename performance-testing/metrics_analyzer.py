"""
QAIP Performance Metrics Analyzer

Reads Locust's CSV output, computes the metrics that actually matter
(P50/P95/P99, throughput, error rate), and compares against the last
known-good baseline to catch performance regressions before they ship —
the same "gate before deploy" philosophy AIPQ uses for prompt quality.
"""

import csv
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class PerfMetrics:
    endpoint: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    requests_per_sec: float
    error_rate_pct: float
    total_requests: int
    total_failures: int


# Regression thresholds — how much worse a metric is allowed to get
# vs. the baseline before the build is blocked. Tune these per endpoint
# as you learn real traffic patterns; these are sane defaults to start.
REGRESSION_THRESHOLDS = {
    "p95_ms_increase_pct": 20,      # P95 latency can't get more than 20% worse
    "error_rate_max_pct": 1.0,      # hard cap — never ship above 1% error rate
    "throughput_decrease_pct": 15,  # RPS can't drop more than 15% vs baseline
}


def parse_locust_stats(csv_path: str) -> list[PerfMetrics]:
    """Locust's --csv flag produces a _stats.csv file with this data."""
    results = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Name"] == "Aggregated":
                continue  # skip the summary row, we want per-endpoint data
            total = int(row["Request Count"])
            failures = int(row["Failure Count"])
            results.append(PerfMetrics(
                endpoint=row["Name"],
                p50_ms=float(row["50%"]),
                p95_ms=float(row["95%"]),
                p99_ms=float(row["99%"]),
                requests_per_sec=float(row["Requests/s"]),
                error_rate_pct=round((failures / total * 100), 2) if total > 0 else 0,
                total_requests=total,
                total_failures=failures,
            ))
    return results


def load_baseline(baseline_path: str) -> dict[str, dict]:
    """Baseline is just the last known-good run's metrics, saved as JSON."""
    path = Path(baseline_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return {m["endpoint"]: m for m in json.load(f)}


def check_regressions(current: list[PerfMetrics], baseline: dict[str, dict]) -> list[str]:
    """
    Returns a list of human-readable regression failures.
    Empty list means the build passes the performance gate.
    """
    failures = []

    for metric in current:
        base = baseline.get(metric.endpoint)

        # Hard cap regardless of baseline — this should never be exceeded
        if metric.error_rate_pct > REGRESSION_THRESHOLDS["error_rate_max_pct"]:
            failures.append(
                f"❌ {metric.endpoint}: error rate {metric.error_rate_pct}% "
                f"exceeds hard cap of {REGRESSION_THRESHOLDS['error_rate_max_pct']}%"
            )

        if base is None:
            continue  # no baseline yet for this endpoint — first run, can't compare

        p95_increase = ((metric.p95_ms - base["p95_ms"]) / base["p95_ms"]) * 100
        if p95_increase > REGRESSION_THRESHOLDS["p95_ms_increase_pct"]:
            failures.append(
                f"❌ {metric.endpoint}: P95 latency regressed {p95_increase:.1f}% "
                f"({base['p95_ms']}ms → {metric.p95_ms}ms)"
            )

        throughput_decrease = ((base["requests_per_sec"] - metric.requests_per_sec)
                                / base["requests_per_sec"]) * 100
        if throughput_decrease > REGRESSION_THRESHOLDS["throughput_decrease_pct"]:
            failures.append(
                f"❌ {metric.endpoint}: throughput dropped {throughput_decrease:.1f}% "
                f"({base['requests_per_sec']} → {metric.requests_per_sec} req/s)"
            )

    return failures


def main():
    if len(sys.argv) < 2:
        print("Usage: python metrics_analyzer.py <locust_stats.csv> [baseline.json]")
        sys.exit(1)

    csv_path = sys.argv[1]
    baseline_path = sys.argv[2] if len(sys.argv) > 2 else "performance-testing/baseline.json"

    current_metrics = parse_locust_stats(csv_path)
    baseline = load_baseline(baseline_path)
    regressions = check_regressions(current_metrics, baseline)

    print("\n=== QAIP Performance Test Results ===\n")
    for m in current_metrics:
        print(f"{m.endpoint}")
        print(f"  P50: {m.p50_ms}ms | P95: {m.p95_ms}ms | P99: {m.p99_ms}ms")
        print(f"  Throughput: {m.requests_per_sec} req/s | Error rate: {m.error_rate_pct}%\n")

    if regressions:
        print("=== REGRESSIONS DETECTED — BUILD FAILED ===")
        for r in regressions:
            print(r)
        sys.exit(1)  # non-zero exit code fails the CI/CD step
    else:
        print("✅ No regressions detected — performance gate passed")
        # Update baseline only on a clean pass, so a bad run never becomes
        # the new "acceptable" standard
        with open(baseline_path, "w") as f:
            json.dump([asdict(m) for m in current_metrics], f, indent=2)
        sys.exit(0)


if __name__ == "__main__":
    main()
