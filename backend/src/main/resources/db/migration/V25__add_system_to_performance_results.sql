-- performance_test_results (V24) was designed for a single system (QAIP).
-- Adding a "system" column so the same table can hold results for other
-- monitored projects (e.g. ARIA) run from the same performance.yml
-- workflow, and the UI can filter by which system a result belongs to.

ALTER TABLE performance_test_results
    ADD COLUMN system VARCHAR(20) NOT NULL DEFAULT 'QAIP';

DROP INDEX IF EXISTS idx_perf_results_endpoint_time;

CREATE INDEX idx_perf_results_system_endpoint_time
    ON performance_test_results (system, endpoint, tested_at DESC);
