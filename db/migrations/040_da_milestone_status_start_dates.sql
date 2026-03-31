-- Migration 040: Add milestone status + start date columns, and referral / change representations stages
--
-- Development.i detail pages show a 4-column milestone table:
--   Description | Status | Start Date | Date Completed
-- Previously we only captured Date Completed. This adds Status and Start Date
-- columns for each milestone, plus two new milestones: Referral and Change Representations.

BEGIN;

-- ── New milestone stages: Referral and Change Representations ──────────────
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS referral_date                  DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS change_representations_date    DATE;

-- ── Milestone status columns ───────────────────────────────────────────────
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS record_creation_status              TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS commence_confirmation_status        TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS properly_made_status                TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS action_notice_response_status       TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS confirmation_notice_sent_status     TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS info_request_sent_status            TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS final_response_received_status      TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS public_notification_status          TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS decision_notice_status              TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS referral_status                     TEXT;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS change_representations_status       TEXT;

-- ── Milestone start-date columns ───────────────────────────────────────────
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS record_creation_start_date              DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS commence_confirmation_start_date        DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS properly_made_start_date                DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS action_notice_response_start_date       DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS confirmation_notice_sent_start_date     DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS info_request_sent_start_date            DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS final_response_received_start_date      DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS public_notification_start_date          DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS decision_notice_start_date              DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS referral_start_date                     DATE;
ALTER TABLE development_applications ADD COLUMN IF NOT EXISTS change_representations_start_date       DATE;

COMMIT;
