-- New Gold Coast City Plan overlay tables.
-- Immutable — refreshed by import_goldcoast_cityplan.py only.

-- Flood assessment required (Layer 81)
CREATE TABLE IF NOT EXISTS qld_goldcoast_flood (
    id        SERIAL PRIMARY KEY,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_flood_geometry
    ON qld_goldcoast_flood USING GIST (geometry);

-- Heritage place (Layer 83)
CREATE TABLE IF NOT EXISTS qld_goldcoast_heritage (
    id                          SERIAL PRIMARY KEY,
    lga_code                    INTEGER,
    cat_desc                    TEXT,
    ovl_cat                     TEXT,
    ovl2_desc                   TEXT,
    ovl2_cat                    TEXT,
    lhr_id                      TEXT,
    place_name                  TEXT,
    assessment_id               TEXT,
    register_status             TEXT,
    qld_heritage_register       TEXT,
    heritage_protection_boundary TEXT,
    adjoining_allotments        TEXT,
    geometry                    geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_heritage_geometry
    ON qld_goldcoast_heritage USING GIST (geometry);

-- Place in proximity to a local heritage place (Layer 84)
CREATE TABLE IF NOT EXISTS qld_goldcoast_heritage_proximity (
    id                    SERIAL PRIMARY KEY,
    lga_code              INTEGER,
    cat_desc              TEXT,
    ovl_cat               TEXT,
    ovl2_desc             TEXT,
    ovl2_cat              TEXT,
    lhr_id                TEXT,
    lot_plan              TEXT,
    assessment_id         TEXT,
    place_name            TEXT,
    qld_heritage_register TEXT,
    geometry              geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_heritage_proximity_geometry
    ON qld_goldcoast_heritage_proximity USING GIST (geometry);

-- Environmental significance (consolidated from layers 48-68)
-- category column identifies the specific sub-layer.
CREATE TABLE IF NOT EXISTS qld_goldcoast_environmental (
    id        SERIAL PRIMARY KEY,
    category  TEXT NOT NULL,
    lga_code  INTEGER,
    cat_desc  TEXT,
    ovl_cat   TEXT,
    ovl2_desc TEXT,
    ovl2_cat  TEXT,
    geometry  geometry(Geometry, 7844)
);
CREATE INDEX IF NOT EXISTS idx_goldcoast_environmental_geometry
    ON qld_goldcoast_environmental USING GIST (geometry);
