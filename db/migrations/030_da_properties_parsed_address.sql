-- Migration 030: Add cadastre suburb + parsed address fields to goldcoast_da_properties
--
-- Populated during enrich by joining to qld_cadastre_address via cadastre_lotplan.

ALTER TABLE goldcoast_da_properties
    ADD COLUMN cadastre_suburb  TEXT,
    ADD COLUMN street_number    TEXT,
    ADD COLUMN street_name      TEXT,
    ADD COLUMN street_type      TEXT,
    ADD COLUMN unit_type        TEXT,
    ADD COLUMN unit_number      TEXT,
    ADD COLUMN unit_suffix      TEXT;
