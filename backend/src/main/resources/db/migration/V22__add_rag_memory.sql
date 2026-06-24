-- ═══════════════════════════════════════════════
-- V22 — Add RAG memory tables for all 4 projects
-- ═══════════════════════════════════════════════

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════
-- QAIP MEMORY
-- Stores test cases, defects, Jira stories as vectors
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS qaip_memory (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL,
    content_type  VARCHAR(50) NOT NULL,
    -- content_type: 'test_case' | 'defect' | 'jira_story' | 'gap_analysis'
    content       TEXT NOT NULL,
    embedding     vector(384),
    module        VARCHAR(100),
    sprint        VARCHAR(50),
    pass_rate     DECIMAL(4,3),
    deepeval_score DECIMAL(4,3),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS qaip_memory_embedding_idx
    ON qaip_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE INDEX IF NOT EXISTS qaip_memory_project_idx
    ON qaip_memory (project_id, content_type);

-- General rag_documents table (used by ai-engine pgvector store)
CREATE TABLE IF NOT EXISTS rag_documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT        NOT NULL,
    embedding   vector(384),
    metadata    JSONB       DEFAULT '{}',
    source_type VARCHAR(50),
    source_id   VARCHAR(255),
    project_id  VARCHAR(255),
    created_at  TIMESTAMP   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_documents_project_idx
    ON rag_documents (project_id, source_type);

CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx
    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- ═══════════════════════════════════════════════
-- SCIP SUPPLIER KNOWLEDGE
-- Stores supplier data as searchable vectors
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scip_supplier_memory (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id   UUID UNIQUE NOT NULL,
    supplier_name VARCHAR(255) NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(384),
    risk_score    DECIMAL(4,3),
    anomaly_flag  BOOLEAN DEFAULT false,
    last_updated  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS scip_supplier_embedding_idx
    ON scip_supplier_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

-- ═══════════════════════════════════════════════
-- ARIA STUDENT KNOWLEDGE
-- Stores uploaded textbook content per student
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS aria_textbook_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID NOT NULL,
    subject     VARCHAR(100) NOT NULL,
    grade       INTEGER NOT NULL,
    chapter     VARCHAR(200),
    content     TEXT NOT NULL,
    embedding   vector(384),
    language    VARCHAR(50) DEFAULT 'English',
    source_file VARCHAR(500),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS aria_textbook_embedding_idx
    ON aria_textbook_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 30);

CREATE INDEX IF NOT EXISTS aria_textbook_student_idx
    ON aria_textbook_memory (student_id, subject);

-- Student learning history
CREATE TABLE IF NOT EXISTS aria_student_progress (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     UUID NOT NULL,
    subject        VARCHAR(100),
    concept        TEXT NOT NULL,
    understood     BOOLEAN NOT NULL,
    struggled_with TEXT,
    embedding      vector(384),
    session_date   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS aria_progress_embedding_idx
    ON aria_student_progress USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

-- ═══════════════════════════════════════════════
-- ZENTRAVIX ORG KNOWLEDGE
-- Stores all org data: Jira, sprint, QAIP, finance
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS zentravix_org_knowledge (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,
    -- source_type: 'jira' | 'sprint' | 'qaip' | 'finance' | 'hr' | 'customer' | 'release'
    source_id   VARCHAR(200),
    department  VARCHAR(100),
    role_access VARCHAR(50) DEFAULT 'ALL',
    content     TEXT NOT NULL,
    embedding   vector(384),
    indexed_at  TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS zentravix_org_source_idx
    ON zentravix_org_knowledge (source_type, source_id);

CREATE INDEX IF NOT EXISTS zentravix_org_embedding_idx
    ON zentravix_org_knowledge USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE INDEX IF NOT EXISTS zentravix_org_role_idx
    ON zentravix_org_knowledge (role_access, department);

-- Alias view for ZENTRAVIX ai-engine vector_store.py (uses zentravix_knowledge table name)
CREATE OR REPLACE VIEW zentravix_knowledge AS
    SELECT
        id::text::bigint  AS id,
        content,
        embedding,
        JSONB_BUILD_OBJECT(
            'source_type', source_type,
            'source_id',   source_id,
            'department',  department,
            'role_access', role_access
        ) AS metadata,
        source_type AS domain,
        source_id   AS entity_id,
        indexed_at  AS updated_at
    FROM zentravix_org_knowledge;
