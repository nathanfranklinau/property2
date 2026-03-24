-- Migration 034: Brisbane DA parsed address columns
--
-- Adds parsed address fields to both parent and child tables,
-- paralleling the Gold Coast DA model (migrations 032-033).
--
-- Parent: mirrors goldcoast_dev_applications (migration 032)
--   Populated by parsing the parent's location_address (extracted from Full Description).
--
-- Child: adds postcode only
--   suburb and cadastre_suburb already exist; suburb = parsed from address text,
--   cadastre_suburb = resolved from lot/plan lookup.
--   Populated during property enrichment.

ALTER TABLE brisbane_dev_applications
    ADD COLUMN street_number TEXT,
    ADD COLUMN street_name   TEXT,
    ADD COLUMN street_type   TEXT,
    ADD COLUMN unit_type     TEXT,
    ADD COLUMN unit_number   TEXT,
    ADD COLUMN unit_suffix   TEXT,
    ADD COLUMN postcode      TEXT;

ALTER TABLE brisbane_da_properties
    ADD COLUMN postcode TEXT;
