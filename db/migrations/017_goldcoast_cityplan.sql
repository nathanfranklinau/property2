-- Gold Coast City Plan Version 13 — Open Data layers
-- Source: https://data-goldcoast.opendata.arcgis.com/maps/0ec7b75a2a794e8eb71c12720c008332/about
-- License: CC BY 4.0
-- Immutable tables — refreshed by import_goldcoast_cityplan.py only
--
-- All attributes stored in JSONB `properties` column (field names vary by layer).
-- Geometry stored in GDA2020 geographic (SRID 7844).

CREATE TABLE IF NOT EXISTS qld_goldcoast_zones (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_zones_geometry
    ON qld_goldcoast_zones USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_building_height (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_building_height_geometry
    ON qld_goldcoast_building_height USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_bushfire_hazard (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_bushfire_hazard_geometry
    ON qld_goldcoast_bushfire_hazard USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_dwelling_house_overlay (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_dwelling_house_overlay_geometry
    ON qld_goldcoast_dwelling_house_overlay USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_buffer_area (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_buffer_area_geometry
    ON qld_goldcoast_buffer_area USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_airport_noise (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_airport_noise_geometry
    ON qld_goldcoast_airport_noise USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_minimum_lot_size (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_minimum_lot_size_geometry
    ON qld_goldcoast_minimum_lot_size USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_party_house (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_party_house_geometry
    ON qld_goldcoast_party_house USING GIST (geometry);

CREATE TABLE IF NOT EXISTS qld_goldcoast_residential_density (
    id          SERIAL PRIMARY KEY,
    properties  JSONB,
    geometry    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_residential_density_geometry
    ON qld_goldcoast_residential_density USING GIST (geometry);
