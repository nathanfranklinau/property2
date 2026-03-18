-- Add lifecycle monitoring columns to goldcoast_dev_applications.
-- Applications with terminal statuses (Completed, Withdrawn, Refused, Lapsed)
-- are marked 'closed' and skipped during periodic monitoring runs.

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN IF NOT EXISTS monitoring_status TEXT NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ;

COMMENT ON COLUMN goldcoast_dev_applications.monitoring_status IS
    'active = needs periodic re-checking; closed = terminal status reached, no further scraping needed';

CREATE INDEX IF NOT EXISTS idx_gc_da_monitoring_status
    ON goldcoast_dev_applications (monitoring_status)
    WHERE monitoring_status = 'active';
