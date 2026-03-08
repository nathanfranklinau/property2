-- Geoscape Administrative Boundaries (all states, GDA2020)
-- Source: https://data.gov.au/data/dataset/geoscape-administrative-boundaries
-- Immutable tables — refreshed by import_admin_boundaries.py only

-- Drop old QLD-only table (replaced by all-states gnaf_admin_lga)
DROP TABLE IF EXISTS qld_lga_boundaries CASCADE;

-- ── Local Government Areas ────────────────────────────────────────────────────
-- Shapefile fields: LG_PLY_PID, LGA_PID, DT_CREATE, LGA_NAME, ABB_NAME, STATE
CREATE TABLE IF NOT EXISTS gnaf_admin_lga (
    id           SERIAL      PRIMARY KEY,
    lg_ply_pid   VARCHAR(15),
    lga_pid      VARCHAR(15),
    lga_name     VARCHAR(75) NOT NULL,
    abb_name     VARCHAR(50),
    state        CHAR(3)     NOT NULL,
    dt_create    DATE,
    geom         geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_gnaf_admin_lga_geom  ON gnaf_admin_lga USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_gnaf_admin_lga_state ON gnaf_admin_lga (state);

-- ── Localities (suburbs/towns) ────────────────────────────────────────────────
-- Shapefile fields: LC_PLY_PID, LOC_PID, DT_CREATE, LOC_NAME, LOC_CLASS, STATE
CREATE TABLE IF NOT EXISTS gnaf_admin_localities (
    id           SERIAL      PRIMARY KEY,
    lc_ply_pid   VARCHAR(15),
    loc_pid      VARCHAR(15),
    loc_name     VARCHAR(50) NOT NULL,
    loc_class    VARCHAR(20),
    state        CHAR(3)     NOT NULL,
    dt_create    DATE,
    geom         geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_gnaf_admin_localities_geom  ON gnaf_admin_localities USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_gnaf_admin_localities_state ON gnaf_admin_localities (state);

-- ── State Boundaries ─────────────────────────────────────────────────────────
-- Shapefile fields: ST_PLY_PID, STATE_PID, DT_CREATE, DT_RETIRE
-- Note: multipart geometry (islands etc.) — many rows per state.
CREATE TABLE IF NOT EXISTS gnaf_admin_state_boundaries (
    id           SERIAL      PRIMARY KEY,
    st_ply_pid   VARCHAR(15),
    state_pid    VARCHAR(15),
    dt_create    DATE,
    dt_retire    DATE,
    geom         geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_gnaf_admin_state_boundaries_geom ON gnaf_admin_state_boundaries USING GIST (geom);

-- ── Council Wards ─────────────────────────────────────────────────────────────
-- Shapefile fields: WD_PLY_PID, WARD_PID, DT_CREATE, WARD_NAME, LGA_PID, STATE
-- Not all states use wards (QLD does not; SA, WA, NT, VIC do).
CREATE TABLE IF NOT EXISTS gnaf_admin_wards (
    id           SERIAL      PRIMARY KEY,
    wd_ply_pid   VARCHAR(15),
    ward_pid     VARCHAR(15),
    ward_name    VARCHAR(75) NOT NULL,
    lga_pid      VARCHAR(15),
    state        CHAR(3)     NOT NULL,
    dt_create    DATE,
    geom         geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_gnaf_admin_wards_geom  ON gnaf_admin_wards USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_gnaf_admin_wards_state ON gnaf_admin_wards (state);
