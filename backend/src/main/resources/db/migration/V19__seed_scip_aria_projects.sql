-- Seed SCIP and ARIA as pre-registered projects in QAIP
-- These are inserted only if they don't already exist

INSERT INTO projects (name, repo_url, tech_stack, status, created_at, updated_at)
SELECT 'SCIP — Supply Chain Intelligence Platform',
       'https://github.com/bkumars22/SupplyChainPlatformProject',
       'Java 17 + Spring Boot + React 18 + Python FastAPI + IsolationForest + LangGraph + PostgreSQL',
       'ACTIVE',
       NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM projects WHERE repo_url = 'https://github.com/bkumars22/SupplyChainPlatformProject'
);

INSERT INTO projects (name, repo_url, tech_stack, status, created_at, updated_at)
SELECT 'ARIA — Adaptive Real-time Intelligence for Anyone',
       'https://github.com/bkumars22/ARIA',
       'Claude AI + LangGraph + React 18 + Spring Boot + Python FastAPI + Whisper STT + PostgreSQL',
       'ACTIVE',
       NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM projects WHERE repo_url = 'https://github.com/bkumars22/ARIA'
);
