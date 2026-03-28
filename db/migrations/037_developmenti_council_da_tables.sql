-- Migration 037: Development.i council DA tables
--
-- Creates parent + child property tables for five QLD councils that use
-- the Development.i portal (same platform as Brisbane):
--   Ipswich, Redland, Sunshine Coast, Toowoomba, Western Downs
--
-- Schema mirrors brisbane_dev_applications / brisbane_da_properties exactly.
-- All share the same Development.i milestone columns.

-- ═══════════════════════════════════════════════════════════════════════
-- Ipswich City Council
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE ipswich_dev_applications (
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
    -- Development.i milestone dates
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    -- Parsed categories
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

CREATE INDEX idx_ips_da_lodgement_date       ON ipswich_dev_applications(lodgement_date);
CREATE INDEX idx_ips_da_status               ON ipswich_dev_applications(status);
CREATE INDEX idx_ips_da_suburb               ON ipswich_dev_applications(suburb);
CREATE INDEX idx_ips_da_application_type     ON ipswich_dev_applications(application_type);
CREATE INDEX idx_ips_da_application_group    ON ipswich_dev_applications(application_group);
CREATE INDEX idx_ips_da_monitoring_status    ON ipswich_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_ips_da_development_category ON ipswich_dev_applications(development_category);
CREATE INDEX idx_ips_da_assessment_level     ON ipswich_dev_applications(assessment_level);

CREATE TABLE ipswich_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES ipswich_dev_applications(application_number) ON DELETE CASCADE,
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

CREATE INDEX idx_ips_da_properties_app_num  ON ipswich_da_properties(application_number);
CREATE INDEX idx_ips_da_properties_cadastre ON ipswich_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_ips_da_properties_land_num ON ipswich_da_properties(land_number)
    WHERE land_number IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════════════
-- Redland City Council
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE redland_dev_applications (
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
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    development_category     TEXT,
    dwelling_type            TEXT,
    unit_count               INTEGER,
    lot_split_from           INTEGER,
    lot_split_to             INTEGER,
    monitoring_status        TEXT DEFAULT 'active',
    status_changed_at        TIMESTAMPTZ,
    first_scraped_at         TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    detail_scraped_at        TIMESTAMPTZ
);

CREATE INDEX idx_rcc_da_lodgement_date       ON redland_dev_applications(lodgement_date);
CREATE INDEX idx_rcc_da_status               ON redland_dev_applications(status);
CREATE INDEX idx_rcc_da_suburb               ON redland_dev_applications(suburb);
CREATE INDEX idx_rcc_da_application_type     ON redland_dev_applications(application_type);
CREATE INDEX idx_rcc_da_application_group    ON redland_dev_applications(application_group);
CREATE INDEX idx_rcc_da_monitoring_status    ON redland_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_rcc_da_development_category ON redland_dev_applications(development_category);
CREATE INDEX idx_rcc_da_assessment_level     ON redland_dev_applications(assessment_level);

CREATE TABLE redland_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES redland_dev_applications(application_number) ON DELETE CASCADE,
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

CREATE INDEX idx_rcc_da_properties_app_num  ON redland_da_properties(application_number);
CREATE INDEX idx_rcc_da_properties_cadastre ON redland_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_rcc_da_properties_land_num ON redland_da_properties(land_number)
    WHERE land_number IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════════════
-- Sunshine Coast Regional Council
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE sunshinecoast_dev_applications (
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
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    development_category     TEXT,
    dwelling_type            TEXT,
    unit_count               INTEGER,
    lot_split_from           INTEGER,
    lot_split_to             INTEGER,
    monitoring_status        TEXT DEFAULT 'active',
    status_changed_at        TIMESTAMPTZ,
    first_scraped_at         TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    detail_scraped_at        TIMESTAMPTZ
);

CREATE INDEX idx_scc_da_lodgement_date       ON sunshinecoast_dev_applications(lodgement_date);
CREATE INDEX idx_scc_da_status               ON sunshinecoast_dev_applications(status);
CREATE INDEX idx_scc_da_suburb               ON sunshinecoast_dev_applications(suburb);
CREATE INDEX idx_scc_da_application_type     ON sunshinecoast_dev_applications(application_type);
CREATE INDEX idx_scc_da_application_group    ON sunshinecoast_dev_applications(application_group);
CREATE INDEX idx_scc_da_monitoring_status    ON sunshinecoast_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_scc_da_development_category ON sunshinecoast_dev_applications(development_category);
CREATE INDEX idx_scc_da_assessment_level     ON sunshinecoast_dev_applications(assessment_level);

CREATE TABLE sunshinecoast_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES sunshinecoast_dev_applications(application_number) ON DELETE CASCADE,
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

CREATE INDEX idx_scc_da_properties_app_num  ON sunshinecoast_da_properties(application_number);
CREATE INDEX idx_scc_da_properties_cadastre ON sunshinecoast_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_scc_da_properties_land_num ON sunshinecoast_da_properties(land_number)
    WHERE land_number IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════════════
-- Toowoomba Regional Council
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE toowoomba_dev_applications (
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
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    development_category     TEXT,
    dwelling_type            TEXT,
    unit_count               INTEGER,
    lot_split_from           INTEGER,
    lot_split_to             INTEGER,
    monitoring_status        TEXT DEFAULT 'active',
    status_changed_at        TIMESTAMPTZ,
    first_scraped_at         TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    detail_scraped_at        TIMESTAMPTZ
);

CREATE INDEX idx_twb_da_lodgement_date       ON toowoomba_dev_applications(lodgement_date);
CREATE INDEX idx_twb_da_status               ON toowoomba_dev_applications(status);
CREATE INDEX idx_twb_da_suburb               ON toowoomba_dev_applications(suburb);
CREATE INDEX idx_twb_da_application_type     ON toowoomba_dev_applications(application_type);
CREATE INDEX idx_twb_da_application_group    ON toowoomba_dev_applications(application_group);
CREATE INDEX idx_twb_da_monitoring_status    ON toowoomba_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_twb_da_development_category ON toowoomba_dev_applications(development_category);
CREATE INDEX idx_twb_da_assessment_level     ON toowoomba_dev_applications(assessment_level);

CREATE TABLE toowoomba_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES toowoomba_dev_applications(application_number) ON DELETE CASCADE,
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

CREATE INDEX idx_twb_da_properties_app_num  ON toowoomba_da_properties(application_number);
CREATE INDEX idx_twb_da_properties_cadastre ON toowoomba_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_twb_da_properties_land_num ON toowoomba_da_properties(land_number)
    WHERE land_number IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════════════
-- Western Downs Regional Council
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE westerndowns_dev_applications (
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
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,
    development_category     TEXT,
    dwelling_type            TEXT,
    unit_count               INTEGER,
    lot_split_from           INTEGER,
    lot_split_to             INTEGER,
    monitoring_status        TEXT DEFAULT 'active',
    status_changed_at        TIMESTAMPTZ,
    first_scraped_at         TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    detail_scraped_at        TIMESTAMPTZ
);

CREATE INDEX idx_wdr_da_lodgement_date       ON westerndowns_dev_applications(lodgement_date);
CREATE INDEX idx_wdr_da_status               ON westerndowns_dev_applications(status);
CREATE INDEX idx_wdr_da_suburb               ON westerndowns_dev_applications(suburb);
CREATE INDEX idx_wdr_da_application_type     ON westerndowns_dev_applications(application_type);
CREATE INDEX idx_wdr_da_application_group    ON westerndowns_dev_applications(application_group);
CREATE INDEX idx_wdr_da_monitoring_status    ON westerndowns_dev_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_wdr_da_development_category ON westerndowns_dev_applications(development_category);
CREATE INDEX idx_wdr_da_assessment_level     ON westerndowns_dev_applications(assessment_level);

CREATE TABLE westerndowns_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES westerndowns_dev_applications(application_number) ON DELETE CASCADE,
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

CREATE INDEX idx_wdr_da_properties_app_num  ON westerndowns_da_properties(application_number);
CREATE INDEX idx_wdr_da_properties_cadastre ON westerndowns_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;
CREATE INDEX idx_wdr_da_properties_land_num ON westerndowns_da_properties(land_number)
    WHERE land_number IS NOT NULL;
