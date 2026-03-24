-- Migration 031: Brisbane development applications tables
--
-- Mirrors the Gold Coast DA pattern (parent + child properties table)
-- but with Brisbane-specific milestone columns from the Development.i portal.

CREATE TABLE brisbane_dev_applications (
    application_number       TEXT PRIMARY KEY,
    description              TEXT,
    application_type         TEXT,
    application_group        TEXT,
    lodgement_date           DATE,
    status                   TEXT,
    decision                 TEXT,
    suburb                   TEXT,
    location_address         TEXT,
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

CREATE INDEX idx_bne_da_lodgement_date     ON brisbane_dev_applications(lodgement_date);
CREATE INDEX idx_bne_da_status             ON brisbane_dev_applications(status);
CREATE INDEX idx_bne_da_suburb             ON brisbane_dev_applications(suburb);
CREATE INDEX idx_bne_da_application_type   ON brisbane_dev_applications(application_type);
CREATE INDEX idx_bne_da_application_group  ON brisbane_dev_applications(application_group);
CREATE INDEX idx_bne_da_monitoring_status  ON brisbane_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_bne_da_development_category ON brisbane_dev_applications(development_category);
CREATE INDEX idx_bne_da_assessment_level   ON brisbane_dev_applications(assessment_level);

-- Child table: one DA can reference multiple properties
CREATE TABLE brisbane_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES brisbane_dev_applications(application_number) ON DELETE CASCADE,
    land_number        TEXT,
    lot_on_plan        TEXT,
    suburb             TEXT,
    location_address   TEXT,
    cadastre_lotplan   TEXT,
    is_primary         BOOLEAN NOT NULL DEFAULT FALSE,
    cadastre_suburb    TEXT,
    street_number      TEXT,
    street_name        TEXT,
    street_type        TEXT,
    unit_type          TEXT,
    unit_number        TEXT,
    unit_suffix        TEXT
);

CREATE INDEX idx_bne_da_properties_app_num  ON brisbane_da_properties(application_number);
CREATE INDEX idx_bne_da_properties_cadastre ON brisbane_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_bne_da_properties_land_num ON brisbane_da_properties(land_number)
    WHERE land_number IS NOT NULL;
