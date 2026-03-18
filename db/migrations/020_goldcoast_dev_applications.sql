-- Gold Coast development applications (scraped from ePathway PD Online)
-- Source: https://cogc.cloud.infor.com/ePathway/epthprod/Web/GeneralEnquiry/EnquiryLists.aspx?ModuleCode=LAP
-- Covers: Development applications lodged after July 2017

CREATE TABLE IF NOT EXISTS goldcoast_dev_applications (
    application_number  TEXT PRIMARY KEY,
    description         TEXT,
    application_type    TEXT,
    lodgement_date      DATE,
    status              TEXT,
    suburb              TEXT,
    location_address    TEXT,
    lot_on_plan         TEXT,

    -- Milestone: Pre-Assessment
    pre_assessment_started      DATE,
    pre_assessment_completed    DATE,

    -- Milestone: Issue Confirmation Notice
    confirmation_notice_started     DATE,
    confirmation_notice_completed   DATE,

    -- Milestone: Decision
    decision_started    DATE,
    decision_completed  DATE,

    -- Document names / descriptions (JSON array of strings)
    documents_summary   JSONB DEFAULT '[]'::jsonb,

    -- Scrape tracking
    first_scraped_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scraped_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detail_scraped_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gc_da_lodgement_date ON goldcoast_dev_applications (lodgement_date);
CREATE INDEX IF NOT EXISTS idx_gc_da_status ON goldcoast_dev_applications (status);
CREATE INDEX IF NOT EXISTS idx_gc_da_suburb ON goldcoast_dev_applications (suburb);
CREATE INDEX IF NOT EXISTS idx_gc_da_application_type ON goldcoast_dev_applications (application_type);
CREATE INDEX IF NOT EXISTS idx_gc_da_lot_on_plan ON goldcoast_dev_applications (lot_on_plan);
