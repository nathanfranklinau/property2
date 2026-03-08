-- QLD Local Government Area boundaries
-- Source: QLD Spatial Catalogue — "Local Government Areas - Queensland"
-- Immutable table — refreshed by import script only

CREATE TABLE IF NOT EXISTS qld_lga_boundaries (
    id         SERIAL PRIMARY KEY,
    lga_name   VARCHAR(200) NOT NULL,
    lga_code   VARCHAR(20),
    geometry   geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_lga_geometry
    ON qld_lga_boundaries USING GIST (geometry);
