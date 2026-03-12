-- Migration 013: Full QLD Cadastre dataset
-- Adds all layers from the QLD DCDB GeoDatabase.
-- These tables are immutable — populated by import scripts only.
-- NEVER add custom columns here.

-- ─────────────────────────────────────────────
-- Add missing columns to existing qld_cadastre_parcels (QLD_CADASTRE_DCDB)
-- ─────────────────────────────────────────────

ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS seg_num      INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS par_num      INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS segpar       INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS par_ind      INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS lot_volume   NUMERIC;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS surv_ind     VARCHAR(1);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS tenure       VARCHAR(40);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS prc          INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS parish       VARCHAR(20);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS county       VARCHAR(16);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS lac          INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS shire_name   VARCHAR(40);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS feat_name    VARCHAR(60);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS alias_name   VARCHAR(400);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS loc          INTEGER;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS locality     VARCHAR(30);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS parcel_typ   VARCHAR(24);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS cover_typ    VARCHAR(10);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS acc_code     VARCHAR(40);
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS ca_area_sqm  NUMERIC;
ALTER TABLE qld_cadastre_parcels ADD COLUMN IF NOT EXISTS smis_map     VARCHAR(100);

-- ─────────────────────────────────────────────
-- QLD Location Address (point locations for addresses)
-- Source layer: QLD_LOCATION_ADDRESS
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_cadastre_address (
    id                  SERIAL          PRIMARY KEY,
    lot                 VARCHAR(5),
    plan                VARCHAR(10),
    lotplan             VARCHAR(15),
    unit_type           VARCHAR(5),
    unit_number         VARCHAR(6),
    unit_suffix         VARCHAR(2),
    floor_type          VARCHAR(5),
    floor_number        VARCHAR(5),
    floor_suffix        VARCHAR(2),
    property_name       VARCHAR(100),
    street_no_1         VARCHAR(11),
    street_no_1_suffix  VARCHAR(2),
    street_no_2         VARCHAR(11),
    street_no_2_suffix  VARCHAR(2),
    street_number       VARCHAR(23),
    street_name         VARCHAR(50),
    street_type         VARCHAR(21),
    street_suffix       VARCHAR(21),
    street_full         VARCHAR(100),
    locality            VARCHAR(41),
    local_authority     VARCHAR(41),
    state               VARCHAR(3),
    address             VARCHAR(300),
    address_status      VARCHAR(1),
    address_standard    VARCHAR(4),
    lotplan_status      VARCHAR(1),
    address_pid         INTEGER,
    geocode_type        VARCHAR(5),
    latitude            NUMERIC,
    longitude           NUMERIC,
    geometry            geometry(Point, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_address_geometry
    ON qld_cadastre_address USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_address_lotplan
    ON qld_cadastre_address (lotplan);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_address_locality
    ON qld_cadastre_address (locality);

-- ─────────────────────────────────────────────
-- QLD Cadastre BUP Lot (Building Unit Plan lots — no geometry)
-- Source layer: QLD_CADASTRE_BUP_LOT
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_cadastre_bup_lot (
    id              SERIAL          PRIMARY KEY,
    lotplan         VARCHAR(15),
    bup_lot         VARCHAR(5),
    bup_plan        VARCHAR(10),
    bup_lotplan     VARCHAR(15),
    lot_area_am     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_bup_lot_lotplan
    ON qld_cadastre_bup_lot (lotplan);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_bup_lot_bup_lotplan
    ON qld_cadastre_bup_lot (bup_lotplan);

-- ─────────────────────────────────────────────
-- QLD Cadastre Natural Boundary (river/creek boundaries)
-- Source layer: QLD_CADASTRE_NATBDY
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_cadastre_natbdy (
    id              SERIAL          PRIMARY KEY,
    linestyle       INTEGER,
    seg_num         INTEGER,
    par_num         INTEGER,
    geometry        geometry(MultiLineString, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_natbdy_geometry
    ON qld_cadastre_natbdy USING GIST (geometry);

-- ─────────────────────────────────────────────
-- QLD Cadastre Road (road centrelines/boundaries)
-- Source layer: QLD_CADASTRE_ROAD
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_cadastre_road (
    id              SERIAL          PRIMARY KEY,
    linestyle       INTEGER,
    seg_num         INTEGER,
    par_num         INTEGER,
    geometry        geometry(MultiLineString, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_road_geometry
    ON qld_cadastre_road USING GIST (geometry);
