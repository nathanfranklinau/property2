-- Migration 033: Add portal_suburb and state columns to goldcoast_da_properties
--
-- portal_suburb: the raw suburb string scraped directly from the ePathway portal,
--   before any cadastre resolution. Distinct from `suburb` (which prefers the
--   authoritative cadastre suburb) and `cadastre_suburb` (resolved via lot/plan).
-- state: jurisdiction — always 'QLD' for Gold Coast DAs.

ALTER TABLE goldcoast_da_properties
    ADD COLUMN portal_suburb  TEXT,
    ADD COLUMN state          TEXT NOT NULL DEFAULT 'QLD';
