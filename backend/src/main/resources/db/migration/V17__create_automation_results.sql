CREATE TABLE automation_results (
    id                  BIGSERIAL PRIMARY KEY,
    execution_id        BIGINT NOT NULL REFERENCES automation_executions(id) ON DELETE CASCADE,
    test_name           VARCHAR(500) NOT NULL,
    test_class          VARCHAR(500),
    status              VARCHAR(20) NOT NULL,  -- PASSED|FAILED|SKIPPED|ERROR
    duration_ms         INT,
    error_message       TEXT,
    stack_trace         TEXT,
    screenshot_base64   TEXT,
    ai_explanation      TEXT,           -- JSON: {root_cause, business_impact, fix_recommendation, severity}
    jira_ticket_key     VARCHAR(50),
    jira_ticket_url     VARCHAR(500),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ar_execution ON automation_results(execution_id);
CREATE INDEX idx_ar_status ON automation_results(status);
CREATE INDEX idx_ar_jira ON automation_results(jira_ticket_key) WHERE jira_ticket_key IS NOT NULL;
