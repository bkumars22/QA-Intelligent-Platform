-- Audit trail for CodegenerateAgent auto-fix attempts (generate_fixes / apply_and_verify_fixes).
-- Deliberately has no FK to pipeline_runs/test_runs: those track a different, existing
-- orchestration and run_id here is a UUID minted independently by the Python AI engine
-- (see ai-engine/main.py /analyze) — no reliable existing row to join against.
CREATE TABLE autofix_audit (
    id            BIGSERIAL PRIMARY KEY,
    run_id        VARCHAR(100) NOT NULL,
    project_id    BIGINT,
    repo_url      TEXT,
    commit_sha    VARCHAR(64),
    file_path     TEXT NOT NULL,
    defect_title  VARCHAR(500) NOT NULL,
    severity      VARCHAR(10),
    branch        VARCHAR(200),
    why           TEXT,
    tests_passed  BOOLEAN,
    status        VARCHAR(30) NOT NULL,
    pr_url        TEXT,
    detail        TEXT,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_autofix_audit_project ON autofix_audit(project_id);
CREATE INDEX idx_autofix_audit_run ON autofix_audit(run_id);
CREATE INDEX idx_autofix_audit_status ON autofix_audit(status);
CREATE INDEX idx_autofix_audit_created_at ON autofix_audit(created_at DESC);
