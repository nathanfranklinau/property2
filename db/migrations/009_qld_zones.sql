-- QLD Planning Scheme Zones
-- Source: QLD Spatial Catalogue — "Planning Scheme Zones"
-- Published by Department of State Development, Infrastructure, Local Government and Planning
-- Immutable table — refreshed by import script only

CREATE TABLE IF NOT EXISTS qld_planning_zones (
    id               SERIAL PRIMARY KEY,
    zone_code        VARCHAR(50),
    zone_name        VARCHAR(200),
    planning_scheme  VARCHAR(200),
    lga              VARCHAR(200),
    geometry         geometry(MultiPolygon, 7844)
);

CREATE INDEX IF NOT EXISTS idx_qld_zones_geometry
    ON qld_planning_zones USING GIST (geometry);
