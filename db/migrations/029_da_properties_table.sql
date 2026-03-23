-- Migration 029: DA properties child table
--
-- Creates goldcoast_da_properties to store all property rows from the
-- ePathway Property section per application (one DA can reference multiple lots).
-- Drops the now-redundant lot_on_plan, lot_plan (generated), and cadastre_lotplan
-- columns from goldcoast_dev_applications.

-- Child table — FK on application_number (the PK of the parent)
CREATE TABLE goldcoast_da_properties (
    id                 SERIAL PRIMARY KEY,
    application_number TEXT NOT NULL REFERENCES goldcoast_dev_applications(application_number) ON DELETE CASCADE,
    lot_on_plan        TEXT,
    suburb             TEXT,
    location_address   TEXT,
    cadastre_lotplan   TEXT,
    is_primary         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_da_properties_app_num  ON goldcoast_da_properties(application_number);
CREATE INDEX idx_da_properties_cadastre ON goldcoast_da_properties(cadastre_lotplan)
    WHERE cadastre_lotplan IS NOT NULL;

-- Drop old columns from parent (lot_plan is generated from lot_on_plan — drop it first)
DROP INDEX IF EXISTS idx_gc_da_lot_on_plan;
DROP INDEX IF EXISTS idx_gc_da_lot_plan;
DROP INDEX IF EXISTS idx_da_cadastre_lotplan;

ALTER TABLE goldcoast_dev_applications DROP COLUMN IF EXISTS lot_plan;
ALTER TABLE goldcoast_dev_applications DROP COLUMN IF EXISTS lot_on_plan;
ALTER TABLE goldcoast_dev_applications DROP COLUMN IF EXISTS cadastre_lotplan;
