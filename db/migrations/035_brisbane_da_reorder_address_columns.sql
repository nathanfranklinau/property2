-- Migration 035: Add + reorder address columns in Brisbane DA tables
--
-- Supersedes migration 034 (which was never applied to this DB).
-- Adds parsed address fields (street_number, street_name, street_type,
-- unit_type, unit_number, unit_suffix, postcode) to the parent table, and
-- postcode to the child table, positioning all parsed address fields
-- immediately after location_address on both tables.
-- PostgreSQL does not support column reordering; this uses table recreation.

BEGIN;

-- ── Parent table ─────────────────────────────────────────────────────────────

-- Drop FK from child first so we can recreate the parent.
ALTER TABLE brisbane_da_properties
    DROP CONSTRAINT brisbane_da_properties_application_number_fkey;

CREATE TABLE brisbane_dev_applications_new (
    application_number       TEXT PRIMARY KEY,
    description              TEXT,
    application_type         TEXT,
    application_group        TEXT,
    lodgement_date           DATE,
    status                   TEXT,
    decision                 TEXT,
    suburb                   TEXT,
    location_address         TEXT,
    -- Parsed address fields
    street_number            TEXT,
    street_name              TEXT,
    street_type              TEXT,
    unit_type                TEXT,
    unit_number              TEXT,
    unit_suffix              TEXT,
    postcode                 TEXT,
    -- Detail fields
    assessment_level         TEXT,
    use_categories           TEXT,
    applicant                TEXT,
    consultant               TEXT,
    assessment_officer       TEXT,
    appeal_result            TEXT,
    -- Brisbane milestone dates (from assessment stages table)
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    -- Parsed categories (same logic as Gold Coast)
    development_category     TEXT,
    dwelling_type            TEXT,
    unit_count               INTEGER,
    lot_split_from           INTEGER,
    lot_split_to             INTEGER,
    -- Monitoring
    monitoring_status        TEXT DEFAULT 'active',
    status_changed_at        TIMESTAMPTZ,
    first_scraped_at         TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    detail_scraped_at        TIMESTAMPTZ
);

-- Parsed address columns are new — they default to NULL for existing rows.
INSERT INTO brisbane_dev_applications_new (
    application_number, description, application_type, application_group,
    lodgement_date, status, decision, suburb, location_address,
    assessment_level, use_categories, applicant, consultant, assessment_officer, appeal_result,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    application_number, description, application_type, application_group,
    lodgement_date, status, decision, suburb, location_address,
    assessment_level, use_categories, applicant, consultant, assessment_officer, appeal_result,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
FROM brisbane_dev_applications;

DROP TABLE brisbane_dev_applications;
ALTER TABLE brisbane_dev_applications_new RENAME TO brisbane_dev_applications;

CREATE INDEX idx_bne_da_lodgement_date       ON brisbane_dev_applications(lodgement_date);
CREATE INDEX idx_bne_da_status               ON brisbane_dev_applications(status);
CREATE INDEX idx_bne_da_suburb               ON brisbane_dev_applications(suburb);
CREATE INDEX idx_bne_da_application_type     ON brisbane_dev_applications(application_type);
CREATE INDEX idx_bne_da_application_group    ON brisbane_dev_applications(application_group);
CREATE INDEX idx_bne_da_monitoring_status    ON brisbane_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_bne_da_development_category ON brisbane_dev_applications(development_category);
CREATE INDEX idx_bne_da_assessment_level     ON brisbane_dev_applications(assessment_level);

-- Restore FK from child table
ALTER TABLE brisbane_da_properties
    ADD CONSTRAINT brisbane_da_properties_application_number_fkey
    FOREIGN KEY (application_number)
    REFERENCES brisbane_dev_applications(application_number)
    ON DELETE CASCADE;

-- ── Child table ──────────────────────────────────────────────────────────────

CREATE TABLE brisbane_da_properties_new (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL,
    land_number        TEXT,
    lot_on_plan        TEXT,
    suburb             TEXT,
    location_address   TEXT,
    -- Parsed address fields
    street_number      TEXT,
    street_name        TEXT,
    street_type        TEXT,
    unit_type          TEXT,
    unit_number        TEXT,
    unit_suffix        TEXT,
    postcode           TEXT,
    -- Cadastre resolution
    cadastre_lotplan   TEXT,
    is_primary         BOOLEAN NOT NULL DEFAULT FALSE,
    cadastre_suburb    TEXT
);

-- postcode is new — defaults to NULL for existing rows.
INSERT INTO brisbane_da_properties_new (
    id, application_number, land_number, lot_on_plan, suburb, location_address,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix,
    cadastre_lotplan, is_primary, cadastre_suburb
)
SELECT
    id, application_number, land_number, lot_on_plan, suburb, location_address,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix,
    cadastre_lotplan, is_primary, cadastre_suburb
FROM brisbane_da_properties;

DROP TABLE brisbane_da_properties;
ALTER TABLE brisbane_da_properties_new RENAME TO brisbane_da_properties;

ALTER TABLE brisbane_da_properties
    ADD CONSTRAINT brisbane_da_properties_application_number_fkey
    FOREIGN KEY (application_number)
    REFERENCES brisbane_dev_applications(application_number)
    ON DELETE CASCADE;

CREATE INDEX idx_bne_da_properties_app_num  ON brisbane_da_properties(application_number);
CREATE INDEX idx_bne_da_properties_cadastre ON brisbane_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_bne_da_properties_land_num ON brisbane_da_properties(land_number)
    WHERE land_number IS NOT NULL;

COMMIT;
