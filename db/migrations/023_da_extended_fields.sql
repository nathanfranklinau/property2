-- Extend goldcoast_dev_applications with additional detail-page fields:
--   - workflow_events: all Work flow/Events rows as JSONB array
--   - decision_type, decision_date, decision_authority: from Decision table
--   - responsible_officer: responsible officer name
--   - dedicated start/finish columns for Decision-Approved, Issue Decision,
--     and End of Applicant Appeal Period workflow events

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS workflow_events              JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS decision_type                TEXT,
    ADD COLUMN IF NOT EXISTS decision_date                DATE,
    ADD COLUMN IF NOT EXISTS decision_authority           TEXT,
    ADD COLUMN IF NOT EXISTS responsible_officer          TEXT,
    ADD COLUMN IF NOT EXISTS decision_approved_started    DATE,
    ADD COLUMN IF NOT EXISTS decision_approved_completed  DATE,
    ADD COLUMN IF NOT EXISTS issue_decision_started       DATE,
    ADD COLUMN IF NOT EXISTS issue_decision_completed     DATE,
    ADD COLUMN IF NOT EXISTS appeal_period_started        DATE,
    ADD COLUMN IF NOT EXISTS appeal_period_completed      DATE;
