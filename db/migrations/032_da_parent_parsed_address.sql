-- Migration 032: Add parsed address columns to goldcoast_dev_applications
--
-- Mirrors the structure already on goldcoast_da_properties (migration 030).
-- Populated during scrape and enrich by parsing the parent location_address field.

ALTER TABLE goldcoast_dev_applications
    ADD COLUMN street_number TEXT,
    ADD COLUMN street_name   TEXT,
    ADD COLUMN street_type   TEXT,
    ADD COLUMN unit_type     TEXT,
    ADD COLUMN unit_number   TEXT,
    ADD COLUMN unit_suffix   TEXT,
    ADD COLUMN postcode      TEXT;
