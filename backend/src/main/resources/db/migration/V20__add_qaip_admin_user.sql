-- Add admin@qaip.io as the canonical QAIP admin account
-- BCrypt hash of 'Admin@2026' with cost 12 (same password, new email)
INSERT INTO users (email, password_hash, role, created_at)
SELECT 'admin@qaip.io',
       '$2a$12$LJfCe0kRKmqnPb3O9JH.S.rXaHzpQlmjFhKTq1.e8t3bF4Y9hSwQy',
       'ADMIN',
       NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'admin@qaip.io'
);

-- Add qa@qaip.io as QA_LEAD
INSERT INTO users (email, password_hash, role, created_at)
SELECT 'qa@qaip.io',
       '$2a$12$LJfCe0kRKmqnPb3O9JH.S.rXaHzpQlmjFhKTq1.e8t3bF4Y9hSwQy',
       'QA_LEAD',
       NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'qa@qaip.io'
);
