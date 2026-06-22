CREATE TABLE generated_reports (
    id              BIGSERIAL PRIMARY KEY,
    execution_id    BIGINT NOT NULL REFERENCES automation_executions(id) ON DELETE CASCADE,
    project_id      BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    html_content    TEXT NOT NULL,
    total_tests     INT NOT NULL DEFAULT 0,
    passed          INT NOT NULL DEFAULT 0,
    failed          INT NOT NULL DEFAULT 0,
    pass_rate       DECIMAL(5,2),
    execution_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    share_token     VARCHAR(64) UNIQUE NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gr_project ON generated_reports(project_id);
CREATE INDEX idx_gr_created ON generated_reports(created_at DESC);
CREATE UNIQUE INDEX idx_gr_share_token ON generated_reports(share_token);
