-- Migration 039: Consolidate all per-council DA tables into unified tables
--
-- Replaces 7 council-specific parent tables and 7 child tables with:
--   development_applications         — one row per DA, all councils
--   development_application_addresses — one row per associated property/address
--
-- Adds lga_pid (from gnaf_admin_lga) and state columns for council identification.
-- Drops all old per-council tables at the end.

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- 1. Create unified parent table
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE development_applications (
    id                        BIGSERIAL PRIMARY KEY,
    lga_pid                   VARCHAR(15) NOT NULL,   -- gnaf_admin_lga.lga_pid
    state                     TEXT NOT NULL DEFAULT 'QLD',
    source_system             TEXT NOT NULL,           -- 'developmenti' | 'epathway'
    application_number        TEXT NOT NULL,
    UNIQUE (lga_pid, application_number),

    -- Common fields (all councils)
    description               TEXT,
    application_type          TEXT,
    application_group         TEXT,
    lodgement_date            DATE,
    status                    TEXT,
    decision                  TEXT,
    suburb                    TEXT,
    location_address          TEXT,
    development_category      TEXT,
    dwelling_type             TEXT,
    unit_count                INTEGER,
    lot_split_from            INTEGER,
    lot_split_to              INTEGER,
    assessment_level          TEXT,
    monitoring_status         TEXT NOT NULL DEFAULT 'active',
    status_changed_at         TIMESTAMPTZ,
    first_scraped_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scraped_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detail_scraped_at         TIMESTAMPTZ,

    -- Development.i specific (NULL for ePathway councils)
    use_categories            TEXT,
    applicant                 TEXT,
    consultant                TEXT,
    assessment_officer        TEXT,
    appeal_result             TEXT,
    public_notification_required TEXT,
    -- Dev.i milestone dates
    record_creation_date             DATE,
    commence_confirmation_date       DATE,
    properly_made_date               DATE,
    action_notice_response_date      DATE,
    confirmation_notice_sent_date    DATE,
    info_request_sent_date           DATE,
    final_response_received_date     DATE,
    public_notification_date         DATE,
    decision_notice_date             DATE,

    -- ePathway / Gold Coast specific (NULL for Dev.i councils)
    epathway_id               INTEGER,
    workflow_events           JSONB DEFAULT '[]',
    documents_summary         JSONB DEFAULT '[]',
    decision_type             TEXT,
    decision_date             DATE,
    decision_authority        TEXT,
    responsible_officer       TEXT,
    -- ePathway milestone date pairs
    pre_assessment_started         DATE,
    pre_assessment_completed       DATE,
    confirmation_notice_started    DATE,
    confirmation_notice_completed  DATE,
    decision_started               DATE,
    decision_completed             DATE,
    decision_approved_started      DATE,
    decision_approved_completed    DATE,
    issue_decision_started         DATE,
    issue_decision_completed       DATE,
    appeal_period_started          DATE,
    appeal_period_completed        DATE
);

CREATE INDEX idx_da_lga_pid              ON development_applications(lga_pid);
CREATE INDEX idx_da_lodgement_date       ON development_applications(lga_pid, lodgement_date);
CREATE INDEX idx_da_status               ON development_applications(lga_pid, status);
CREATE INDEX idx_da_development_category ON development_applications(development_category);
CREATE INDEX idx_da_monitoring_status    ON development_applications(monitoring_status)
    WHERE monitoring_status = 'active';
CREATE INDEX idx_da_application_type     ON development_applications(application_type);
CREATE INDEX idx_da_assessment_level     ON development_applications(assessment_level);
CREATE INDEX idx_da_suburb               ON development_applications(suburb);

-- ═══════════════════════════════════════════════════════════════════════
-- 2. Create unified child table
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE development_application_addresses (
    id                SERIAL PRIMARY KEY,
    application_id    BIGINT NOT NULL REFERENCES development_applications(id) ON DELETE CASCADE,
    land_number       TEXT,
    lot_on_plan       TEXT,
    suburb            TEXT,
    location_address  TEXT,
    street_number     TEXT,
    street_name       TEXT,
    street_type       TEXT,
    unit_type         TEXT,
    unit_number       TEXT,
    unit_suffix       TEXT,
    postcode          TEXT,
    cadastre_lotplan  TEXT,
    is_primary        BOOLEAN NOT NULL DEFAULT FALSE,
    cadastre_suburb   TEXT
);

CREATE INDEX idx_daa_application_id ON development_application_addresses(application_id);
CREATE INDEX idx_daa_cadastre       ON development_application_addresses(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════
-- 3. Migrate data from each council
-- ═══════════════════════════════════════════════════════════════════════

-- Brisbane (Development.i) — lga_pid: lgaf711db11e308
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lgaf711db11e308', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM brisbane_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM brisbane_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lgaf711db11e308' AND da.application_number = p.application_number;


-- Ipswich (Development.i) — lga_pid: lgafd22606d6b20
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lgafd22606d6b20', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM ipswich_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM ipswich_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lgafd22606d6b20' AND da.application_number = p.application_number;


-- Redland (Development.i) — lga_pid: lga42379c2c72f3
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lga42379c2c72f3', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM redland_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM redland_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lga42379c2c72f3' AND da.application_number = p.application_number;


-- Sunshine Coast (Development.i) — lga_pid: lgaa9ec4359b5d6
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lgaa9ec4359b5d6', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM sunshinecoast_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM sunshinecoast_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lgaa9ec4359b5d6' AND da.application_number = p.application_number;


-- Toowoomba (Development.i) — lga_pid: lga59db913dcc12
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lga59db913dcc12', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM toowoomba_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM toowoomba_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lga59db913dcc12' AND da.application_number = p.application_number;


-- Western Downs (Development.i) — lga_pid: lga1be86b7b4de2
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    monitoring_status, status_changed_at, first_scraped_at, last_scraped_at, detail_scraped_at
)
SELECT
    'lga1be86b7b4de2', 'QLD', 'developmenti', application_number,
    description, application_type, application_group, lodgement_date, status,
    decision, suburb, location_address, assessment_level, use_categories,
    applicant, consultant, assessment_officer, appeal_result,
    public_notification_required,
    record_creation_date, commence_confirmation_date, properly_made_date,
    action_notice_response_date, confirmation_notice_sent_date,
    info_request_sent_date, final_response_received_date,
    public_notification_date, decision_notice_date,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    COALESCE(monitoring_status, 'active'), status_changed_at,
    COALESCE(first_scraped_at, NOW()), COALESCE(last_scraped_at, NOW()), detail_scraped_at
FROM westerndowns_dev_applications;

INSERT INTO development_application_addresses (
    application_id, land_number, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type, unit_type, unit_number, unit_suffix
)
SELECT da.id, p.land_number, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type, p.unit_type, p.unit_number, p.unit_suffix
FROM westerndowns_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lga1be86b7b4de2' AND da.application_number = p.application_number;


-- Gold Coast (ePathway) — lga_pid: lgaaeff9c47295f
-- Parent data
INSERT INTO development_applications (
    lga_pid, state, source_system, application_number,
    description, application_type, lodgement_date, status,
    suburb, location_address,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    assessment_level, monitoring_status, status_changed_at,
    first_scraped_at, last_scraped_at, detail_scraped_at,
    epathway_id, workflow_events, documents_summary,
    decision_type, decision_date, decision_authority, responsible_officer,
    pre_assessment_started, pre_assessment_completed,
    confirmation_notice_started, confirmation_notice_completed,
    decision_started, decision_completed,
    decision_approved_started, decision_approved_completed,
    issue_decision_started, issue_decision_completed,
    appeal_period_started, appeal_period_completed
)
SELECT
    'lgaaeff9c47295f', 'QLD', 'epathway', application_number,
    description, application_type, lodgement_date, status,
    suburb, location_address,
    development_category, dwelling_type, unit_count, lot_split_from, lot_split_to,
    assessment_level, monitoring_status, status_changed_at,
    first_scraped_at, last_scraped_at, detail_scraped_at,
    epathway_id, workflow_events, documents_summary,
    decision_type, decision_date, decision_authority, responsible_officer,
    pre_assessment_started, pre_assessment_completed,
    confirmation_notice_started, confirmation_notice_completed,
    decision_started, decision_completed,
    decision_approved_started, decision_approved_completed,
    issue_decision_started, issue_decision_completed,
    appeal_period_started, appeal_period_completed
FROM goldcoast_dev_applications;

-- Gold Coast child table data (goldcoast_da_properties exists)
INSERT INTO development_application_addresses (
    application_id, lot_on_plan, suburb, location_address,
    cadastre_lotplan, is_primary, cadastre_suburb,
    street_number, street_name, street_type,
    unit_type, unit_number, unit_suffix
)
SELECT da.id, p.lot_on_plan, p.suburb, p.location_address,
       p.cadastre_lotplan, p.is_primary, p.cadastre_suburb,
       p.street_number, p.street_name, p.street_type,
       p.unit_type, p.unit_number, p.unit_suffix
FROM goldcoast_da_properties p
JOIN development_applications da
  ON da.lga_pid = 'lgaaeff9c47295f' AND da.application_number = p.application_number;


-- ═══════════════════════════════════════════════════════════════════════
-- 4. Drop old tables
-- ═══════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS brisbane_da_properties CASCADE;
DROP TABLE IF EXISTS brisbane_dev_applications CASCADE;
DROP TABLE IF EXISTS ipswich_da_properties CASCADE;
DROP TABLE IF EXISTS ipswich_dev_applications CASCADE;
DROP TABLE IF EXISTS redland_da_properties CASCADE;
DROP TABLE IF EXISTS redland_dev_applications CASCADE;
DROP TABLE IF EXISTS sunshinecoast_da_properties CASCADE;
DROP TABLE IF EXISTS sunshinecoast_dev_applications CASCADE;
DROP TABLE IF EXISTS toowoomba_da_properties CASCADE;
DROP TABLE IF EXISTS toowoomba_dev_applications CASCADE;
DROP TABLE IF EXISTS westerndowns_da_properties CASCADE;
DROP TABLE IF EXISTS westerndowns_dev_applications CASCADE;
DROP TABLE IF EXISTS goldcoast_da_properties CASCADE;
DROP TABLE IF EXISTS goldcoast_dev_applications CASCADE;

COMMIT;
