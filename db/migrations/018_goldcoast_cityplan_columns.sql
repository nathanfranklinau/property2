-- Rebuild Gold Coast City Plan tables with explicit columns.
-- Replaces the JSONB approach from 017.
-- Immutable tables — refreshed by import_goldcoast_cityplan.py only.

DROP TABLE IF EXISTS qld_goldcoast_zones;
CREATE TABLE qld_goldcoast_zones (
    id               SERIAL PRIMARY KEY,
    zone_precinct    TEXT,
    lvl1_zone        TEXT,
    lga_code         INTEGER,
    zone             TEXT,
    building_height  TEXT,
    bh_category      TEXT,
    geometry         geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_zones_geometry
    ON qld_goldcoast_zones USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_building_height;
CREATE TABLE qld_goldcoast_building_height (
    id               SERIAL PRIMARY KEY,
    lga_code         INTEGER,
    cat_desc         TEXT,
    ovl_cat          TEXT,
    ovl2_desc        TEXT,
    ovl2_cat         TEXT,
    height_in_metres TEXT,
    storey_number    TEXT,
    label            TEXT,
    height_label     TEXT,
    geometry         geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_building_height_geometry
    ON qld_goldcoast_building_height USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_bushfire_hazard;
CREATE TABLE qld_goldcoast_bushfire_hazard (
    id        SERIAL PRIMARY KEY,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_bushfire_hazard_geometry
    ON qld_goldcoast_bushfire_hazard USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_dwelling_house_overlay;
CREATE TABLE qld_goldcoast_dwelling_house_overlay (
    id        SERIAL PRIMARY KEY,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_dwelling_house_overlay_geometry
    ON qld_goldcoast_dwelling_house_overlay USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_buffer_area;
CREATE TABLE qld_goldcoast_buffer_area (
    id       SERIAL PRIMARY KEY,
    geometry geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_buffer_area_geometry
    ON qld_goldcoast_buffer_area USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_airport_noise;
CREATE TABLE qld_goldcoast_airport_noise (
    id                SERIAL PRIMARY KEY,
    lga_code          INTEGER,
    cat_desc          TEXT,
    ovl_cat           TEXT,
    ovl2_desc         TEXT,
    ovl2_cat          TEXT,
    sensitive_use_type TEXT,
    buffer_source     TEXT,
    buffer_distance   TEXT,
    geometry          geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_airport_noise_geometry
    ON qld_goldcoast_airport_noise USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_minimum_lot_size;
CREATE TABLE qld_goldcoast_minimum_lot_size (
    id        SERIAL PRIMARY KEY,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    mls       TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_minimum_lot_size_geometry
    ON qld_goldcoast_minimum_lot_size USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_party_house;
CREATE TABLE qld_goldcoast_party_house (
    id        SERIAL PRIMARY KEY,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_party_house_geometry
    ON qld_goldcoast_party_house USING GIST (geometry);

DROP TABLE IF EXISTS qld_goldcoast_residential_density;
CREATE TABLE qld_goldcoast_residential_density (
    id                   SERIAL PRIMARY KEY,
    lga_code             INTEGER,
    cat_desc             TEXT,
    ovl_cat              TEXT,
    ovl2_desc            TEXT,
    ovl2_cat             TEXT,
    residential_density  TEXT,
    geometry             geometry(Geometry, 7844)
);
CREATE INDEX idx_goldcoast_residential_density_geometry
    ON qld_goldcoast_residential_density USING GIST (geometry);
