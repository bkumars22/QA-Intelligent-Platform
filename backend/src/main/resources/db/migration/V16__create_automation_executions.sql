CREATE TABLE automation_executions (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    framework_profile_id BIGINT REFERENCES framework_profiles(id),
    suite_name          VARCHAR(255) NOT NULL,
    framework_type      VARCHAR(20) NOT NULL,
    app_url             VARCHAR(500),
    generated_code      TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'QUEUED', -- QUEUED|RUNNING|PASSED|FAILED|ERROR
    total_tests         INT NOT NULL DEFAULT 0,
    passed              INT NOT NULL DEFAULT 0,
    failed              INT NOT NULL DEFAULT 0,
    skipped             INT NOT NULL DEFAULT 0,
    duration_ms         BIGINT,
    triggered_by        VARCHAR(255),
    commit_sha          VARCHAR(40),
    report_url          VARCHAR(500),
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ae_project ON automation_executions(project_id);
CREATE INDEX idx_ae_status ON automation_executions(status);
CREATE INDEX idx_ae_created ON automation_executions(created_at DESC);
