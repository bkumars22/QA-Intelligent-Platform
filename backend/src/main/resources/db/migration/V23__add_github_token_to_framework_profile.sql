-- Add github_token column so QAIP can read/write spec files back to GitHub
ALTER TABLE framework_profiles
    ADD COLUMN IF NOT EXISTS github_token VARCHAR(500);
