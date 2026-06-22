CREATE TABLE framework_profiles (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    framework_type      VARCHAR(20) NOT NULL,          -- PLAYWRIGHT | SELENIUM
    repo_url            VARCHAR(500) NOT NULL,
    branch              VARCHAR(100) NOT NULL DEFAULT 'main',
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING|ANALYSING|CONNECTED|FAILED
    error_message       TEXT,
    base_class          VARCHAR(500),
    folder_structure    JSONB,
    naming_conventions  JSONB,
    import_patterns     JSONB,
    hook_patterns       JSONB,
    custom_utilities    JSONB,
    page_objects_count  INT,
    test_files_count    INT,
    summary_text        TEXT,
    analysed_at         TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uix_framework_project ON framework_profiles(project_id, framework_type);
CREATE INDEX idx_framework_project ON framework_profiles(project_id);
