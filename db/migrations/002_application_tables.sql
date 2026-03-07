-- Migration 002: Application tables
-- These are owned by the app and safe to modify via future migrations.
-- See docs/architecture.md for schema design rationale.

-- ─────────────────────────────────────────────────────────────────
-- parcels
-- App-owned cache of cadastre data for properties users have looked up.
-- Populated by Next.js when an address is searched.
-- geometry and dimensions are derived from qld_cadastre_parcels.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS parcels (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    cadastre_lot    VARCHAR(10)     NOT NULL,
    cadastre_plan   VARCHAR(20)     NOT NULL,
    state           VARCHAR(3)      NOT NULL DEFAULT 'QLD',
    lot_area_sqm    NUMERIC(12,2),
    frontage_m      NUMERIC(8,2),   -- width of primary road frontage
    depth_m         NUMERIC(8,2),   -- average depth of parcel
    display_address VARCHAR(500),   -- human-readable address for display
    geometry        geometry(MultiPolygon, 7844),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (cadastre_lot, cadastre_plan)
);

CREATE INDEX IF NOT EXISTS idx_parcels_lot_plan
    ON parcels (cadastre_lot, cadastre_plan);

CREATE INDEX IF NOT EXISTS idx_parcels_geometry
    ON parcels USING GIST (geometry);

-- ─────────────────────────────────────────────────────────────────
-- property_analysis
-- One row per parcel. Shared cache — if two users look up the same
-- property, they both read from the same analysis row.
-- The Python analysis service writes to this table.
-- image_status and analysis_status are updated as pipeline progresses.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS property_analysis (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_id               UUID            NOT NULL REFERENCES parcels(id) ON DELETE CASCADE,

    -- Pipeline status (updated by Python service as each step completes)
    image_status            VARCHAR(20)     NOT NULL DEFAULT 'pending'
                                CHECK (image_status IN ('pending', 'downloading', 'complete', 'failed')),
    analysis_status         VARCHAR(20)     NOT NULL DEFAULT 'pending'
                                CHECK (analysis_status IN ('pending', 'detecting', 'complete', 'failed')),

    -- Image file paths (relative to IMAGES_DIR env var)
    image_roadmap_path      VARCHAR(500),
    image_satellite_path    VARCHAR(500),
    image_markup_path       VARCHAR(500),   -- roadmap annotated with detected building outlines

    -- Building detection results
    main_house_size_sqm     NUMERIC(10,2),
    building_count          INTEGER,

    -- Space calculation
    available_space_sqm     NUMERIC(10,2),

    -- Pool results
    pool_count_detected     INTEGER         DEFAULT 0,
    pool_count_registered   INTEGER         DEFAULT 0,
    pool_area_sqm           NUMERIC(10,2)   DEFAULT 0,

    -- Error handling
    error_message           TEXT,

    analyzed_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- One analysis per parcel
    UNIQUE (parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_property_analysis_parcel
    ON property_analysis (parcel_id);

-- ─────────────────────────────────────────────────────────────────
-- Phase 2 tables (auth + journey)
-- Not required for prototyping — add in a later migration.
-- Defined here as comments for reference.
-- ─────────────────────────────────────────────────────────────────

-- users
--   id UUID PK, email VARCHAR UNIQUE, password_hash VARCHAR, created_at

-- user_properties
--   id UUID PK, user_id UUID FK users, parcel_id UUID FK parcels, created_at

-- subdivision_assessments
--   id UUID PK, parcel_id UUID FK parcels, meets_minimum_lot_size BOOL,
--   frontage_adequate BOOL, zoning_permits BOOL, has_constraints BOOL,
--   assessment_notes JSONB, recommended_action VARCHAR, created_at

-- subdivision_journeys
--   id UUID PK, user_property_id UUID FK user_properties,
--   jurisdiction VARCHAR(10) DEFAULT 'QLD',
--   status VARCHAR CHECK ('not_started','in_progress','complete','on_hold'),
--   started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, created_at

-- journey_steps (seeded per jurisdiction, not per user)
--   id UUID PK, jurisdiction VARCHAR, step_order INT, stage VARCHAR,
--   title VARCHAR, description TEXT, category VARCHAR, is_required BOOL,
--   typical_cost_low INT, typical_cost_high INT, reference_url VARCHAR
--   UNIQUE (jurisdiction, step_order)

-- journey_step_completions
--   id UUID PK, journey_id UUID FK subdivision_journeys,
--   step_id UUID FK journey_steps, completed_at TIMESTAMPTZ,
--   notes TEXT, document_urls JSONB
--   UNIQUE (journey_id, step_id)
