-- Migration 001: Immutable dataset tables
-- These tables are populated by Python import scripts.
-- NEVER add custom columns here — they will be lost when datasets are refreshed.

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- ─────────────────────────────────────────────
-- GNAF Tables
-- Source: Geocoded National Address File (GNAF) February 2026
-- Column order matches PSV file order exactly (required for COPY FROM STDIN)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS gnaf_state (
    state_pid            VARCHAR(15)  PRIMARY KEY,
    date_created         DATE         NOT NULL,
    date_retired         DATE,
    state_name           VARCHAR(50)  NOT NULL,
    state_abbreviation   VARCHAR(3)   NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_locality (
    locality_pid         VARCHAR(15)  PRIMARY KEY,
    date_created         DATE         NOT NULL,
    date_retired         DATE,
    locality_name        VARCHAR(100) NOT NULL,
    primary_postcode     VARCHAR(4),
    locality_class_code  VARCHAR(1)   NOT NULL,
    state_pid            VARCHAR(15)  NOT NULL REFERENCES gnaf_state(state_pid),
    gnaf_locality_pid    VARCHAR(15),
    gnaf_reliability_code INTEGER
);

CREATE TABLE IF NOT EXISTS gnaf_address_detail (
    address_detail_pid          VARCHAR(15)  PRIMARY KEY,
    date_created                DATE         NOT NULL,
    date_last_modified          DATE,
    date_retired                DATE,
    building_name               VARCHAR(200),
    lot_number_prefix           VARCHAR(2),
    lot_number                  VARCHAR(5),
    lot_number_suffix           VARCHAR(2),
    flat_type_code              VARCHAR(7),
    flat_number_prefix          VARCHAR(2),
    flat_number                 NUMERIC(5),
    flat_number_suffix          VARCHAR(2),
    level_type_code             VARCHAR(4),
    level_number_prefix         VARCHAR(2),
    level_number                NUMERIC(3),
    level_number_suffix         VARCHAR(2),
    number_first_prefix         VARCHAR(3),
    number_first                NUMERIC(6),
    number_first_suffix         VARCHAR(2),
    number_last_prefix          VARCHAR(3),
    number_last                 NUMERIC(6),
    number_last_suffix          VARCHAR(2),
    street_locality_pid         VARCHAR(15),
    location_description        VARCHAR(45),
    locality_pid                VARCHAR(15)  NOT NULL REFERENCES gnaf_locality(locality_pid),
    alias_principal             CHAR(1),
    postcode                    VARCHAR(4),
    private_street              VARCHAR(75),
    legal_parcel_id             VARCHAR(20),
    confidence                  NUMERIC(1),
    address_site_pid            VARCHAR(15)  NOT NULL,
    level_geocoded_code         NUMERIC(2)   NOT NULL,
    property_pid                VARCHAR(15),
    gnaf_property_pid           VARCHAR(15),
    primary_secondary           VARCHAR(1)
);

-- PSV column order: ADDRESS_SITE_GEOCODE_PID|DATE_CREATED|DATE_RETIRED|
--   ADDRESS_SITE_PID|GEOCODE_SITE_NAME|GEOCODE_SITE_DESCRIPTION|
--   GEOCODE_TYPE_CODE|RELIABILITY_CODE|BOUNDARY_EXTENT|PLANIMETRIC_ACCURACY|
--   ELEVATION|LONGITUDE|LATITUDE
-- geometry is populated separately after COPY via ST_MakePoint(longitude, latitude)
CREATE TABLE IF NOT EXISTS gnaf_address_site_geocode (
    address_site_geocode_pid    VARCHAR(15)  PRIMARY KEY,
    date_created                DATE         NOT NULL,
    date_retired                DATE,
    address_site_pid            VARCHAR(15),
    geocode_site_name           VARCHAR(200),
    geocode_site_description    VARCHAR(45),
    geocode_type_code           VARCHAR(4),
    reliability_code            NUMERIC(1)   NOT NULL,
    boundary_extent             NUMERIC(7),
    planimetric_accuracy        NUMERIC(12),
    elevation                   NUMERIC(7),
    longitude                   NUMERIC(11,8),
    latitude                    NUMERIC(10,8),
    geometry                    geometry(Point, 7844)
);

CREATE INDEX IF NOT EXISTS idx_gnaf_geocode_geometry
    ON gnaf_address_site_geocode USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_gnaf_geocode_address_site
    ON gnaf_address_site_geocode (address_site_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_address_detail_locality
    ON gnaf_address_detail (locality_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_address_detail_postcode
    ON gnaf_address_detail (postcode);

CREATE INDEX IF NOT EXISTS idx_gnaf_address_detail_address_site
    ON gnaf_address_detail (address_site_pid);

-- ─────────────────────────────────────────────────────────────────────────────
-- QLD Cadastre
-- Source: QLD DCDB (DP_QLD_DCDB_WOS_CUR_GDA2020.gdb), layer QLD_CADASTRE_DCDB
-- Fields confirmed from ogrinfo: LOT, PLAN, LOTPLAN, LOT_AREA, EXCL_AREA,
--   LOT_VOLUME, SEG_NUM, PAR_NUM, SEGPAR, PAR_IND, SURV_IND
-- Note: shire_name/locality/tenure not present in this GDB version
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_cadastre_parcels (
    id              SERIAL          PRIMARY KEY,
    lot             VARCHAR(5),
    plan            VARCHAR(10),
    lotplan         VARCHAR(15),    -- combined lot/plan identifier (e.g. "1SP123456")
    lot_area        NUMERIC,        -- square metres (unbounded — GDB Real field)
    excl_area       NUMERIC,        -- excluded area in square metres
    geometry        geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_geometry
    ON qld_cadastre_parcels USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_lot_plan
    ON qld_cadastre_parcels (lot, plan);

CREATE INDEX IF NOT EXISTS idx_qld_cadastre_lotplan
    ON qld_cadastre_parcels (lotplan);

-- ─────────────────────────────────────────────
-- QLD Registered Pools
-- Source: QLD Government pool registry CSV
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS qld_pools_registered (
    id                      SERIAL          PRIMARY KEY,
    site_name               VARCHAR(200)    NOT NULL UNIQUE,
    unit_number             VARCHAR(20),
    street_number           VARCHAR(20),
    street_name             VARCHAR(200),
    street_type             VARCHAR(50),
    suburb                  VARCHAR(100),
    postcode                VARCHAR(4),
    number_of_pools         INTEGER,
    lga                     VARCHAR(200),
    shared_pool_property    VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_qld_pools_suburb
    ON qld_pools_registered (suburb);

CREATE INDEX IF NOT EXISTS idx_qld_pools_postcode
    ON qld_pools_registered (postcode);
