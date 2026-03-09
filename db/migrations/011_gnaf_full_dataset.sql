-- Migration 011: Full GNAF dataset
-- All tables from the Geocoded National Address File (G-NAF) February 2026.
-- Prefixed with gnaf_data_ to distinguish from the earlier partial gnaf_ tables.
-- These tables are IMMUTABLE — populated by import script, never modified by app code.

-- ═══════════════════════════════════════════════════════════════════════════════
-- Authority Code (reference/lookup) tables — loaded first, no FK dependencies
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS gnaf_data_address_alias_type_aut (
    code        varchar(10)  NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(30)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_change_type_aut (
    code        varchar(50)  NOT NULL PRIMARY KEY,
    name        varchar(100) NOT NULL,
    description varchar(500)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_type_aut (
    code        varchar(8)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(30)
);

CREATE TABLE IF NOT EXISTS gnaf_data_flat_type_aut (
    code        varchar(7)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(30)
);

CREATE TABLE IF NOT EXISTS gnaf_data_geocoded_level_type_aut (
    code        numeric(2)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(70)
);

CREATE TABLE IF NOT EXISTS gnaf_data_geocode_reliability_aut (
    code        numeric(1)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(100)
);

CREATE TABLE IF NOT EXISTS gnaf_data_geocode_type_aut (
    code        varchar(4)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(250)
);

CREATE TABLE IF NOT EXISTS gnaf_data_level_type_aut (
    code        varchar(4)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(30)
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality_alias_type_aut (
    code        varchar(10)  NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(100)
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality_class_aut (
    code        char(1)      NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(200)
);

CREATE TABLE IF NOT EXISTS gnaf_data_mb_match_code_aut (
    code        varchar(15)  NOT NULL PRIMARY KEY,
    name        varchar(100) NOT NULL,
    description varchar(250)
);

CREATE TABLE IF NOT EXISTS gnaf_data_ps_join_type_aut (
    code        numeric(2)   NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(500)
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_class_aut (
    code        char(1)      NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(200)
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_locality_alias_type_aut (
    code        varchar(10)  NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(15)
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_suffix_aut (
    code        varchar(15)  NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(30)
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_type_aut (
    code        varchar(15)  NOT NULL PRIMARY KEY,
    name        varchar(50)  NOT NULL,
    description varchar(15)
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Standard tables — loaded per state, FK order matters
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS gnaf_data_state (
    state_pid          varchar(15) NOT NULL PRIMARY KEY,
    date_created       date        NOT NULL,
    date_retired       date,
    state_name         varchar(50) NOT NULL,
    state_abbreviation varchar(3)  NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality (
    locality_pid          varchar(15)  NOT NULL PRIMARY KEY,
    date_created          date         NOT NULL,
    date_retired          date,
    locality_name         varchar(100) NOT NULL,
    primary_postcode      varchar(4),
    locality_class_code   char(1)      NOT NULL,
    state_pid             varchar(15)  NOT NULL,
    gnaf_locality_pid     varchar(15),
    gnaf_reliability_code numeric(1)   NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality_alias (
    locality_alias_pid varchar(15)  NOT NULL PRIMARY KEY,
    date_created       date         NOT NULL,
    date_retired       date,
    locality_pid       varchar(15)  NOT NULL,
    name               varchar(100) NOT NULL,
    postcode           varchar(4),
    alias_type_code    varchar(10)  NOT NULL,
    state_pid          varchar(15)  NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality_neighbour (
    locality_neighbour_pid varchar(15) NOT NULL PRIMARY KEY,
    date_created           date        NOT NULL,
    date_retired           date,
    locality_pid           varchar(15) NOT NULL,
    neighbour_locality_pid varchar(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_locality_point (
    locality_point_pid   varchar(15)   NOT NULL PRIMARY KEY,
    date_created         date          NOT NULL,
    date_retired         date,
    locality_pid         varchar(15)   NOT NULL,
    planimetric_accuracy numeric(12),
    longitude            numeric(11,8),
    latitude             numeric(10,8)
);

CREATE TABLE IF NOT EXISTS gnaf_data_mb_2016 (
    mb_2016_pid  varchar(15) NOT NULL PRIMARY KEY,
    date_created date        NOT NULL,
    date_retired date,
    mb_2016_code varchar(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_mb_2021 (
    mb_2021_pid  varchar(15) NOT NULL PRIMARY KEY,
    date_created date        NOT NULL,
    date_retired date,
    mb_2021_code varchar(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_locality (
    street_locality_pid     varchar(15)  NOT NULL PRIMARY KEY,
    date_created            date         NOT NULL,
    date_retired            date,
    street_class_code       char(1)      NOT NULL,
    street_name             varchar(100) NOT NULL,
    street_type_code        varchar(15),
    street_suffix_code      varchar(15),
    locality_pid            varchar(15)  NOT NULL,
    gnaf_street_pid         varchar(15),
    gnaf_street_confidence  numeric(1),
    gnaf_reliability_code   numeric(1)   NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_locality_alias (
    street_locality_alias_pid varchar(15)  NOT NULL PRIMARY KEY,
    date_created              date         NOT NULL,
    date_retired              date,
    street_locality_pid       varchar(15)  NOT NULL,
    street_name               varchar(100) NOT NULL,
    street_type_code          varchar(15),
    street_suffix_code        varchar(15),
    alias_type_code           varchar(10)  NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_street_locality_point (
    street_locality_point_pid varchar(15)   NOT NULL PRIMARY KEY,
    date_created              date          NOT NULL,
    date_retired              date,
    street_locality_pid       varchar(15)   NOT NULL,
    boundary_extent           numeric(7),
    planimetric_accuracy      numeric(12),
    longitude                 numeric(11,8),
    latitude                  numeric(10,8)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_site (
    address_site_pid  varchar(15)  NOT NULL PRIMARY KEY,
    date_created      date         NOT NULL,
    date_retired      date,
    address_type      varchar(8),
    address_site_name varchar(200)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_detail (
    address_detail_pid     varchar(15)  NOT NULL PRIMARY KEY,
    date_created           date         NOT NULL,
    date_last_modified     date,
    date_retired           date,
    building_name          varchar(200),
    lot_number_prefix      varchar(2),
    lot_number             varchar(5),
    lot_number_suffix      varchar(2),
    flat_type_code         varchar(7),
    flat_number_prefix     varchar(2),
    flat_number            numeric(5),
    flat_number_suffix     varchar(2),
    level_type_code        varchar(4),
    level_number_prefix    varchar(2),
    level_number           numeric(3),
    level_number_suffix    varchar(2),
    number_first_prefix    varchar(3),
    number_first           numeric(6),
    number_first_suffix    varchar(2),
    number_last_prefix     varchar(3),
    number_last            numeric(6),
    number_last_suffix     varchar(2),
    street_locality_pid    varchar(15),
    location_description   varchar(45),
    locality_pid           varchar(15)  NOT NULL,
    alias_principal        char(1),
    postcode               varchar(4),
    private_street         varchar(75),
    legal_parcel_id        varchar(20),
    confidence             numeric(1),
    address_site_pid       varchar(15)  NOT NULL,
    level_geocoded_code    numeric(2)   NOT NULL,
    property_pid           varchar(15),
    gnaf_property_pid      varchar(15),
    primary_secondary      varchar(1)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_site_geocode (
    address_site_geocode_pid varchar(15)   NOT NULL PRIMARY KEY,
    date_created             date          NOT NULL,
    date_retired             date,
    address_site_pid         varchar(15),
    geocode_site_name        varchar(200),
    geocode_site_description varchar(45),
    geocode_type_code        varchar(4),
    reliability_code         numeric(1)    NOT NULL,
    boundary_extent          numeric(7),
    planimetric_accuracy     numeric(12),
    elevation                numeric(7),
    longitude                numeric(11,8),
    latitude                 numeric(10,8),
    -- PostGIS geometry column (populated after COPY via UPDATE)
    geometry                 geometry(Point, 7844)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_default_geocode (
    address_default_geocode_pid varchar(15)   NOT NULL PRIMARY KEY,
    date_created                date          NOT NULL,
    date_retired                date,
    address_detail_pid          varchar(15)   NOT NULL,
    geocode_type_code           varchar(4)    NOT NULL,
    longitude                   numeric(11,8),
    latitude                    numeric(10,8),
    -- PostGIS geometry column (populated after COPY via UPDATE)
    geometry                    geometry(Point, 7844)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_alias (
    address_alias_pid varchar(15)  NOT NULL PRIMARY KEY,
    date_created      date         NOT NULL,
    date_retired      date,
    principal_pid     varchar(15)  NOT NULL,
    alias_pid         varchar(15)  NOT NULL,
    alias_type_code   varchar(10)  NOT NULL,
    alias_comment     varchar(200)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_feature (
    address_feature_id          varchar(16) NOT NULL PRIMARY KEY,
    address_feature_pid         varchar(16) NOT NULL,
    address_detail_pid          varchar(15) NOT NULL,
    date_address_detail_created date        NOT NULL,
    date_address_detail_retired date,
    address_change_type_code    varchar(50)
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_mesh_block_2016 (
    address_mesh_block_2016_pid varchar(15) NOT NULL PRIMARY KEY,
    date_created                date        NOT NULL,
    date_retired                date,
    address_detail_pid          varchar(15) NOT NULL,
    mb_match_code               varchar(15) NOT NULL,
    mb_2016_pid                 varchar(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_address_mesh_block_2021 (
    address_mesh_block_2021_pid varchar(15) NOT NULL PRIMARY KEY,
    date_created                date        NOT NULL,
    date_retired                date,
    address_detail_pid          varchar(15) NOT NULL,
    mb_match_code               varchar(15) NOT NULL,
    mb_2021_pid                 varchar(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS gnaf_data_primary_secondary (
    primary_secondary_pid varchar(15)  NOT NULL PRIMARY KEY,
    primary_pid           varchar(15)  NOT NULL,
    secondary_pid         varchar(15)  NOT NULL,
    date_created          date         NOT NULL,
    date_retired          date,
    ps_join_type_code     numeric(2)   NOT NULL,
    ps_join_comment       varchar(500)
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Indexes for common query patterns
-- ═══════════════════════════════════════════════════════════════════════════════

-- Spatial indexes on geocode tables
CREATE INDEX IF NOT EXISTS idx_gnaf_data_site_geocode_geometry
    ON gnaf_data_address_site_geocode USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_default_geocode_geometry
    ON gnaf_data_address_default_geocode USING GIST (geometry);

-- Address detail lookups
CREATE INDEX IF NOT EXISTS idx_gnaf_data_address_detail_locality
    ON gnaf_data_address_detail (locality_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_address_detail_postcode
    ON gnaf_data_address_detail (postcode);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_address_detail_address_site
    ON gnaf_data_address_detail (address_site_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_address_detail_street_locality
    ON gnaf_data_address_detail (street_locality_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_address_detail_legal_parcel
    ON gnaf_data_address_detail (legal_parcel_id);

-- Site geocode → address site join
CREATE INDEX IF NOT EXISTS idx_gnaf_data_site_geocode_address_site
    ON gnaf_data_address_site_geocode (address_site_pid);

-- Default geocode → address detail join
CREATE INDEX IF NOT EXISTS idx_gnaf_data_default_geocode_address_detail
    ON gnaf_data_address_default_geocode (address_detail_pid);

-- Street locality lookups
CREATE INDEX IF NOT EXISTS idx_gnaf_data_street_locality_locality
    ON gnaf_data_street_locality (locality_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_street_locality_name
    ON gnaf_data_street_locality (street_name);

-- Locality lookups
CREATE INDEX IF NOT EXISTS idx_gnaf_data_locality_state
    ON gnaf_data_locality (state_pid);

CREATE INDEX IF NOT EXISTS idx_gnaf_data_locality_name
    ON gnaf_data_locality (locality_name);
