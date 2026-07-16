-- Flyway migration: adds performance test history, so QAIP can show
-- trend lines over time (is P95 creeping up build over build?), not
-- just pass/fail on the latest run.

CREATE TABLE performance_test_results (
    id              BIGSERIAL PRIMARY KEY,
    build_sha       VARCHAR(64) NOT NULL,
    endpoint        VARCHAR(255) NOT NULL,
    p50_ms          NUMERIC(10, 2) NOT NULL,
    p95_ms          NUMERIC(10, 2) NOT NULL,
    p99_ms          NUMERIC(10, 2) NOT NULL,
    requests_per_sec NUMERIC(10, 2) NOT NULL,
    error_rate_pct  NUMERIC(5, 2) NOT NULL,
    total_requests  INTEGER NOT NULL,
    total_failures  INTEGER NOT NULL,
    passed_gate     BOOLEAN NOT NULL,
    tested_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookups for "show me the last 30 days of P95 for this endpoint"
CREATE INDEX idx_perf_results_endpoint_time
    ON performance_test_results (endpoint, tested_at DESC);

COMMENT ON TABLE performance_test_results IS
    'Historical performance test runs. Feeds the trend dashboard and
     lets QAIP flag slow-creeping regressions that a single-run
     threshold check would miss (e.g. P95 up 5% every build for a month).';
