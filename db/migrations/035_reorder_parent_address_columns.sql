-- Migration 035: Move parsed address columns next to location_address
--   on goldcoast_dev_applications.
--
-- PostgreSQL does not support ALTER TABLE ... REORDER COLUMNS, so the table
-- is recreated with the desired layout and all data copied across.
--
-- The child table (goldcoast_da_properties) holds a FK ON DELETE CASCADE
-- referencing this table; that constraint is temporarily dropped and recreated.

BEGIN;

CREATE TABLE goldcoast_dev_applications_new (
    application_number  TEXT PRIMARY KEY,
    description         TEXT,
    application_type    TEXT,
    lodgement_date      DATE,
    status              TEXT,

    -- Portal suburb (raw from ePathway summary row)
    suburb              TEXT,

    -- Address (raw portal value + parsed components)
    location_address    TEXT,
    street_number       TEXT,
    street_name         TEXT,
    street_type         TEXT,
    unit_type           TEXT,
    unit_number         TEXT,
    unit_suffix         TEXT,
    postcode            TEXT,
    -- Authoritative locality from resolving the primary child lot/plan
    cadastre_suburb     TEXT,

    -- Milestone: Pre-Assessment
    pre_assessment_started      DATE,
    pre_assessment_completed    DATE,

    -- Milestone: Issue Confirmation Notice
    confirmation_notice_started     DATE,
    confirmation_notice_completed   DATE,

    -- Milestone: Decision
    decision_started    DATE,
    decision_completed  DATE,

    -- Decision detail
    decision_type       TEXT,
    decision_date       DATE,
    decision_authority  TEXT,
    decision_approved_started    DATE,
    decision_approved_completed  DATE,
    issue_decision_started       DATE,
    issue_decision_completed     DATE,
    appeal_period_started        DATE,
    appeal_period_completed      DATE,

    -- Parsed description fields
    development_category TEXT,
    dwelling_type        TEXT,
    unit_count           INTEGER,
    lot_split_from       INTEGER,
    lot_split_to         INTEGER,
    assessment_level     TEXT,

    -- Staff / workflow
    responsible_officer  TEXT,
    workflow_events      JSONB DEFAULT '[]'::jsonb,
    documents_summary    JSONB DEFAULT '[]'::jsonb,

    -- Scrape tracking
    epathway_id          INTEGER,
    monitoring_status    TEXT NOT NULL DEFAULT 'active',
    status_changed_at    TIMESTAMPTZ,
    first_scraped_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detail_scraped_at    TIMESTAMPTZ
);

INSERT INTO goldcoast_dev_applications_new (
    application_number, description, application_type, lodgement_date, status,
    suburb, location_address,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix,
    postcode, cadastre_suburb,
    pre_assessment_started, pre_assessment_completed,
    confirmation_notice_started, confirmation_notice_completed,
    decision_started, decision_completed,
    decision_type, decision_date, decision_authority,
    decision_approved_started, decision_approved_completed,
    issue_decision_started, issue_decision_completed,
    appeal_period_started, appeal_period_completed,
    development_category, dwelling_type, unit_count,
    lot_split_from, lot_split_to, assessment_level,
    responsible_officer, workflow_events, documents_summary,
    epathway_id, monitoring_status, status_changed_at,
    first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    application_number, description, application_type, lodgement_date, status,
    suburb, location_address,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix,
    postcode, cadastre_suburb,
    pre_assessment_started, pre_assessment_completed,
    confirmation_notice_started, confirmation_notice_completed,
    decision_started, decision_completed,
    decision_type, decision_date, decision_authority,
    decision_approved_started, decision_approved_completed,
    issue_decision_started, issue_decision_completed,
    appeal_period_started, appeal_period_completed,
    development_category, dwelling_type, unit_count,
    lot_split_from, lot_split_to, assessment_level,
    responsible_officer, workflow_events, documents_summary,
    epathway_id, monitoring_status, status_changed_at,
    first_scraped_at, last_scraped_at, detail_scraped_at
FROM goldcoast_dev_applications;

-- Drop the FK on the child table before dropping the parent
ALTER TABLE goldcoast_da_properties
    DROP CONSTRAINT goldcoast_da_properties_application_number_fkey;

DROP TABLE goldcoast_dev_applications;

ALTER TABLE goldcoast_dev_applications_new RENAME TO goldcoast_dev_applications;

-- Restore FK on child table
ALTER TABLE goldcoast_da_properties
    ADD CONSTRAINT goldcoast_da_properties_application_number_fkey
    FOREIGN KEY (application_number)
    REFERENCES goldcoast_dev_applications(application_number)
    ON DELETE CASCADE;

-- Recreate indexes
CREATE INDEX idx_gc_da_lodgement_date    ON goldcoast_dev_applications (lodgement_date);
CREATE INDEX idx_gc_da_status            ON goldcoast_dev_applications (status);
CREATE INDEX idx_gc_da_suburb            ON goldcoast_dev_applications (suburb);
CREATE INDEX idx_gc_da_application_type  ON goldcoast_dev_applications (application_type);
CREATE INDEX idx_gc_da_epathway_id       ON goldcoast_dev_applications (epathway_id);
CREATE INDEX idx_gc_da_development_category ON goldcoast_dev_applications (development_category);
CREATE INDEX idx_gc_da_dwelling_type     ON goldcoast_dev_applications (dwelling_type);
CREATE INDEX idx_gc_da_assessment_level  ON goldcoast_dev_applications (assessment_level);
CREATE INDEX idx_gc_da_monitoring_status ON goldcoast_dev_applications (monitoring_status)
    WHERE monitoring_status = 'active';

COMMENT ON COLUMN goldcoast_dev_applications.monitoring_status IS
    'active = needs periodic re-checking; closed = terminal status reached, no further scraping needed';

COMMIT;
